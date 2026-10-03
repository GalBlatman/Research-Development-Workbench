import math
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderConfig:
    provider: str = "fake"
    model: str = "gpt-6-sol"
    timeout: float = 30
    reasoning_effort: str | None = "low"
    max_output_tokens: int = 6000
    max_context_bytes: int = 150000
    max_input_tokens: int = 200000
    max_calls: int = 4
    max_run_tokens: int = 500000
    retries: int = 1
    input_rate: float = 2
    cached_rate: float = 0.2
    cache_write_rate: float = 2.5
    output_rate: float = 10
    price_date: str = "2026-10-02"

    def __post_init__(self) -> None:
        if self.provider not in ("fake", "openai"):
            raise ValueError("Unsupported configured provider")
        if not self.model or not 1 <= self.timeout <= 120:
            raise ValueError("Invalid model/timeout configuration")
        if self.reasoning_effort not in (None, "none", "low", "medium", "high", "xhigh", "max"):
            raise ValueError("Invalid reasoning effort")
        if not (1 <= self.max_calls <= 6 and 0 <= self.retries <= 2):
            raise ValueError("Invalid bounded call/retry configuration")
        if (
            min(
                self.max_output_tokens,
                self.max_context_bytes,
                self.max_input_tokens,
                self.max_run_tokens,
            )
            <= 0
        ):
            raise ValueError("Budgets must be positive")
        if self.max_output_tokens > 128000 or any(
            not math.isfinite(rate) or rate < 0
            for rate in (self.input_rate, self.cached_rate, self.cache_write_rate, self.output_rate)
        ):
            raise ValueError("Invalid output limit or cost inputs")

    @classmethod
    def environment(cls) -> "ProviderConfig":
        model = os.getenv("RDW_MODEL", "gpt-6-sol")
        if model != "gpt-6-sol" and os.getenv("RDW_PROVIDER", "fake") == "openai":
            if not all(
                os.getenv(k)
                for k in (
                    "RDW_INPUT_RATE",
                    "RDW_CACHED_RATE",
                    "RDW_CACHE_WRITE_RATE",
                    "RDW_OUTPUT_RATE",
                    "RDW_PRICE_DATE",
                )
            ):
                raise ValueError("Alternate models require explicit dated price inputs")
        return cls(
            provider=os.getenv("RDW_PROVIDER", "fake"),
            model=model,
            timeout=float(os.getenv("RDW_REQUEST_TIMEOUT", "30")),
            reasoning_effort=os.getenv("RDW_REASONING_EFFORT", "low") or None,
            max_output_tokens=int(os.getenv("RDW_MAX_OUTPUT_TOKENS", "6000")),
            max_context_bytes=int(os.getenv("RDW_MAX_CONTEXT_BYTES", "150000")),
            max_input_tokens=int(os.getenv("RDW_MAX_INPUT_TOKENS", "200000")),
            max_calls=int(os.getenv("RDW_MAX_CALLS", "4")),
            max_run_tokens=int(os.getenv("RDW_MAX_RUN_TOKENS", "500000")),
            retries=int(os.getenv("RDW_RETRIES", "1")),
            input_rate=float(os.getenv("RDW_INPUT_RATE", "2")),
            cached_rate=float(os.getenv("RDW_CACHED_RATE", "0.2")),
            cache_write_rate=float(os.getenv("RDW_CACHE_WRITE_RATE", "2.5")),
            output_rate=float(os.getenv("RDW_OUTPUT_RATE", "10")),
            price_date=os.getenv("RDW_PRICE_DATE", "2026-10-02"),
        )
