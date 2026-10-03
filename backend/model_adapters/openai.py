import hashlib
import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel

from domain.application import (
    AssessmentTask,
    CandidateReview,
    CheckingTask,
    CheckResult,
    Interpretation,
    InterpretationTask,
)
from domain.models import ProviderCall, ProviderRun
from domain.research import (
    WorkspaceCheckingTask,
    WorkspaceCheckResult,
    WorkspaceProposal,
    WorkspaceTask,
)
from model_adapters.config import ProviderConfig
from model_adapters.runtime import ProviderFailure, active, provider_session, timestamp
from model_adapters.schema import strict_schema

T = TypeVar("T", bound=BaseModel)
PROMPTS = Path(__file__).resolve().parents[1] / "prompts"
DERIVED = {
    "ROUTE-TOTAL",
    "DISCOVERY-PENDING",
    "UNINSPECTED-BLOCK",
    "HIGH-SCORE-BENCHMARK",
    "EDITORIAL-UNCALIBRATED",
}


def policy_contract(task: AssessmentTask) -> dict[str, Any]:
    if task.policy_version not in ("4", "5"):
        raise ProviderFailure("UNKNOWN_POLICY_VERSION")
    manifest = json.loads(
        (PROMPTS.parents[1] / f"policies/rubric-v{task.policy_version}.manifest.json").read_text(
            encoding="utf-8"
        )
    )
    criteria = json.loads((PROMPTS / "criteria-v1.json").read_text(encoding="utf-8"))
    dimensions = task.dimensions or tuple(range(1, 11))
    # Numerical arithmetic/caps/weights never enter model instructions.
    meanings = {
        "AUDIENCE-QUESTION": "Audience or question cannot be identified",
        "PREMISE-NO-BASIS": "Central asserted phenomenon has neither support nor credible establishing plan",
        "PREMISE-CONDITIONAL": "Central asserted phenomenon lacks support but has credible establishing plan",
        "PREMISE-CONTRADICTED": "Evidence contradicts retained indispensable premise",
        "NO-ADVANCE": "EXPLAIN only applies an existing answer without nontrivial advance",
        "NO-CONSEQUENTIAL-STAKE": "Surprise has no concrete consequential scholarly, organizational or societal stake",
        "DESIGN-MISMATCH": "Central question and design do not match",
        "INFERENCE-UNSUPPORTED": "Evidence cannot support central promised kind of inference",
        "PROMISE-OVERREACH": "Contribution promise exceeds argument and evidence",
        "STAGE-MISMATCH": "Central mismatch defeats proposed stage",
    }
    rules = (
        []
        if task.dimensions
        else [
            {
                "id": r["id"],
                "source": r["source"],
                "predicate": meanings.get(r["id"], r["consequence"]),
            }
            for r in manifest["rules"]
            if r["id"] not in DERIVED
            and (task.context.project.route == "EXPLAIN" or r["id"] != "NO-ADVANCE")
        ]
    )
    route_questions = json.loads((PROMPTS / "route-questions-v1.json").read_text(encoding="utf-8"))
    if task.policy_version == "5" and task.context.project.route != "EXPLAIN":
        criteria = {
            key: "Not applicable numerical dimension for this route; use supplied qualitative route questions without theory-profile scoring."
            if int(key) <= 7
            else value
            for key, value in criteria.items()
        }
    if (
        task.policy_version == "5"
        and task.context.project.route == "EXPLAIN"
        and task.context.project.stage in ("EARLY IDEA", "DISCOVERY PROPOSAL")
    ):
        route_questions = {
            **route_questions,
            "EXPLAIN": {
                "knowledge_need": "Is there a consequential knowledge need?",
                "increment": "Is there an identifiable prospective knowledge increment?",
                "capacity_to_learn": "Is there a credible resource-bounded action to address the main uncertainty?",
            },
        }
    return {
        **(
            {"route_questions": route_questions[task.context.project.route]}
            if task.context.project.route in route_questions and not task.dimensions
            else {}
        ),
        "dimensions": {str(d): criteria[str(d)] for d in dimensions},
        "semantic_rules": rules,
        "rating_reference": "0 absent/inadequate; 5 solid accepted-paper reference; 8 exceptional with supplied published comparison; 10 decade-class element, not paper perfection. Uninspected is null, not zero.",
        "principal_obstacle_contract": "Include statement_id=principal-obstacle with text exactly matching summary.obstacle; attribute it honestly.",
    }


def packet_check(context: Any) -> None:
    if any(
        p.source.project_id != context.project.project_id
        or p.source.workspace_id != context.project.workspace_id
        for p in context.passages
    ):
        raise ProviderFailure("CONTEXT_SCOPE_MISMATCH")
    for passage in context.passages:
        if (
            passage.anchor.document_id != passage.source.document_id
            or hashlib.sha256(passage.text.encode()).hexdigest()
            != passage.anchor.quoted_text_sha256
        ):
            raise ProviderFailure("CONTEXT_ANCHOR_MISMATCH")


class OpenAIAdapter:
    prompt_configuration = "evaluation-v3/checking-v4/workspace-v2/workspace-check-v2"

    def __init__(
        self,
        config: ProviderConfig,
        client: httpx.Client | None = None,
        receipt_sink: Callable[[ProviderRun], None] | None = None,
    ):
        self.provider_config = config
        self.receipt_sink = receipt_sink
        self.configuration = "openai:" + config.model
        self.client = client or httpx.Client(
            timeout=config.timeout, trust_env=False, follow_redirects=False
        )

    def close(self) -> None:
        self.client.close()

    def interpret(self, task: InterpretationTask) -> Interpretation:
        packet_check(task.context)
        with provider_session(self):
            return self.call("interpretation", task.model_dump(mode="json"), Interpretation)

    def assess(self, task: AssessmentTask) -> CandidateReview:
        packet_check(task.context)
        with provider_session(self):
            payload = task.model_dump(mode="json")
            payload["criteria"] = policy_contract(task)
            return self.call("evaluation", payload, CandidateReview)

    def check(self, task: CheckingTask) -> CheckResult:
        packet_check(task.assessment_task.context)
        with provider_session(self):
            payload = task.model_dump(mode="json")
            payload["criteria"] = policy_contract(task.assessment_task)
            return self.call("checking", payload, CheckResult)

    def develop(self, task: WorkspaceTask) -> WorkspaceProposal:
        packet_check(task.context)
        with provider_session(self):
            return self.call("workspace", task.model_dump(mode="json"), WorkspaceProposal)

    def workspace_check(self, task: WorkspaceCheckingTask) -> WorkspaceCheckResult:
        packet_check(task.context)
        with provider_session(self):
            return self.call("workspace-check", task.model_dump(mode="json"), WorkspaceCheckResult)

    def call(self, kind: str, payload: dict[str, Any], model: type[T]) -> T:
        config = self.provider_config
        packet = payload.get("context") or payload.get("assessment_task", {}).get("context")
        if len(json.dumps(packet, ensure_ascii=False).encode()) > config.max_context_bytes:
            raise ProviderFailure("CONTEXT_LIMIT")
        prompt_version = kind + (
            "-v4"
            if kind == "checking"
            else "-v3"
            if kind == "evaluation"
            else "-v2"
            if kind in ("baseline", "workspace", "workspace-check")
            else "-v1"
        )
        prompt = (PROMPTS / (prompt_version + ".md")).read_text(encoding="utf-8")
        prompt_hash = hashlib.sha256(
            (
                prompt + json.dumps(payload.get("criteria", {}), sort_keys=True, ensure_ascii=False)
            ).encode()
        ).hexdigest()
        body: dict[str, Any] = {
            "model": config.model,
            "store": False,
            "background": False,
            "instructions": prompt,
            "input": json.dumps(payload, ensure_ascii=False),
            "max_output_tokens": config.max_output_tokens,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "rdw_" + kind,
                    "strict": True,
                    "schema": strict_schema(model),
                }
            },
        }
        if config.reasoning_effort is not None:
            body["reasoning"] = {"effort": config.reasoning_effort}
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise ProviderFailure("BLOCKED_CREDENTIAL")
        ledger = active.get()
        assert ledger is not None
        # UTF-8 bytes conservatively bound textual input tokens, including schema/instructions.
        input_bound = len(json.dumps(body, ensure_ascii=False).encode()) + 1024
        for attempt in range(config.retries + 1):
            reserved = ledger.reserve(input_bound)
            started = timestamp()
            response: httpx.Response | None = None
            data: dict[str, Any] = {}
            status = "PROVIDER_ERROR"
            result: T | None = None
            transient = False
            try:
                response = self.client.post(
                    "https://api.openai.com/v1/responses",
                    json=body,
                    headers={"Authorization": "Bearer " + key},
                    timeout=config.timeout,
                )
                if response.status_code >= 400:
                    transient = response.status_code == 429 or response.status_code >= 500
                    try:
                        error = response.json().get("error", {})
                    except ValueError:
                        error = {}
                    error_code = error.get("code") if isinstance(error, dict) else None
                    status = {
                        401: "AUTHENTICATION_FAILED",
                        403: "PERMISSION_DENIED",
                        404: "MODEL_UNAVAILABLE",
                        413: "CONTEXT_LIMIT",
                        429: "RATE_LIMIT",
                    }.get(
                        response.status_code,
                        "TRANSIENT_PROVIDER_ERROR"
                        if response.status_code >= 500
                        else "INVALID_REQUEST",
                    )
                    if error_code in ("context_length_exceeded", "max_tokens_exceeded"):
                        status = "CONTEXT_LIMIT"
                else:
                    data = response.json()
                    if not isinstance(data, dict):
                        raise ValueError("Malformed provider envelope")
                    output = data.get("output", [])
                    contents = [
                        c
                        for item in output
                        if item.get("type") == "message"
                        for c in item.get("content", [])
                    ]
                    if any(c.get("type") == "refusal" for c in contents):
                        status = "REFUSAL"
                    elif data.get("status") == "incomplete":
                        status = "INCOMPLETE_OUTPUT"
                    elif data.get("status") != "completed":
                        status = "PROVIDER_ERROR"
                    elif any(item.get("type") not in ("message", "reasoning") for item in output):
                        status = "UNEXPECTED_TOOL_OUTPUT"
                    else:
                        texts = [c["text"] for c in contents if c.get("type") == "output_text"]
                        if len(texts) != 1:
                            raise ValueError("Missing structured result")
                        result = model.model_validate_json(texts[0])
                        returned = data.get("model")
                        import re

                        if not isinstance(returned, str) or not (
                            returned == config.model
                            or re.fullmatch(
                                re.escape(config.model) + r"-\d{4}-\d{2}-\d{2}", returned
                            )
                        ):
                            result, status = None, "MODEL_MISMATCH"
                        else:
                            status = "SUCCEEDED"
            except httpx.TimeoutException:
                status = "TIMEOUT_UNCERTAIN"
            except httpx.HTTPError:
                status = "TRANSPORT_ERROR_UNCERTAIN"
            except (ValueError, TypeError, KeyError, AttributeError):
                status = "MALFORMED_OUTPUT"
            if not isinstance(data, dict):
                data = {}
            usage = data.get("usage") or {}
            if not isinstance(usage, dict):
                usage = {}
                status, result = "MALFORMED_OUTPUT", None
            details: dict[str, int] = {}
            for group in ("input_tokens_details", "output_tokens_details"):
                counters = usage.get(group) or {}
                if not isinstance(counters, dict):
                    status, result = "MALFORMED_OUTPUT", None
                    counters = {}
                for name, value in counters.items():
                    if isinstance(value, int) and not isinstance(value, bool):
                        details[group + "." + name] = value
            inp, out = usage.get("input_tokens"), usage.get("output_tokens")
            if status == "SUCCEEDED" and (
                not isinstance(inp, int)
                or isinstance(inp, bool)
                or not isinstance(out, int)
                or isinstance(out, bool)
            ):
                status, result = "USAGE_UNAVAILABLE", None
            if isinstance(inp, int) and isinstance(out, int):
                if inp < 0 or out < 0 or inp > input_bound or out > config.max_output_tokens:
                    status, result = "BUDGET_EXHAUSTED", None
                # Reservations remain consumed even after success: no uncertain charge refund.
            ledger.calls.append(
                ProviderCall(
                    task=kind,
                    provider="openai",
                    configured_model=config.model,
                    returned_model=data.get("model")
                    if isinstance(data.get("model"), str)
                    else None,
                    timestamp=started,
                    prompt_version=prompt_version,
                    prompt_sha256=prompt_hash,
                    status=status,
                    request_id=response.headers.get("x-request-id")
                    if response is not None
                    else None,
                    input_tokens=inp if isinstance(inp, int) else None,
                    output_tokens=out if isinstance(out, int) else None,
                    usage_details=details,
                    reserved_tokens=reserved,
                    input_usd_per_million=config.input_rate,
                    cached_input_usd_per_million=config.cached_rate,
                    cache_write_usd_per_million=config.cache_write_rate,
                    output_usd_per_million=config.output_rate,
                    price_date=config.price_date,
                )
            )
            if self.receipt_sink is not None:
                self.receipt_sink(ledger.receipt())
            if result is not None and status == "SUCCEEDED":
                return result
            if not transient or attempt >= config.retries:
                raise ProviderFailure(status)
        raise ProviderFailure("PROVIDER_ERROR")
