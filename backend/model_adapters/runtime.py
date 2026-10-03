from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from domain.models import ProviderCall, ProviderRun
from model_adapters.config import ProviderConfig


class ProviderFailure(ValueError):
    def __init__(self, code: str, metadata: ProviderRun | None = None):
        super().__init__(code)
        self.code = code
        self.metadata = metadata


@dataclass
class Ledger:
    config: ProviderConfig
    run_id: str = field(default_factory=lambda: uuid4().hex)
    calls: list[ProviderCall] = field(default_factory=list)
    reserved: int = 0
    state: str = "RUNNING"

    def reserve(self, input_bound: int) -> int:
        amount = input_bound + self.config.max_output_tokens
        if (
            input_bound > self.config.max_input_tokens
            or len(self.calls) >= self.config.max_calls
            or self.reserved + amount > self.config.max_run_tokens
        ):
            raise ProviderFailure("BUDGET_EXHAUSTED")
        self.reserved += amount
        return amount

    def receipt(self) -> ProviderRun:
        return ProviderRun(
            run_id=self.run_id,
            status=self.state,
            calls=tuple(self.calls),
            max_calls=self.config.max_calls,
            max_tokens=self.config.max_run_tokens,
            output_limit=self.config.max_output_tokens,
            reasoning_effort=self.config.reasoning_effort,
        )


active: ContextVar[Ledger | None] = ContextVar("provider_ledger", default=None)


def timestamp() -> str:
    return datetime.now(UTC).isoformat()


@contextmanager
def provider_session(adapter: Any) -> Iterator[Ledger | None]:
    config = getattr(adapter, "provider_config", None)
    if config is None:
        yield None
        return
    previous = active.get()
    if previous is not None:
        yield previous
        return
    ledger = Ledger(config)
    token = active.set(ledger)
    try:
        yield ledger
        ledger.state = "SUCCEEDED"
    except BaseException as exc:
        ledger.state = "FAILED"
        if isinstance(exc, ProviderFailure):
            exc.metadata = ledger.receipt()
        raise
    finally:
        active.reset(token)
        record = getattr(adapter, "receipt_sink", None)
        if record is not None:
            record(ledger.receipt())
