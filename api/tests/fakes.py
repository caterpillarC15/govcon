"""Shared test doubles for skill tests."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from api.llm import LLM, LLMMetrics


class FakeLLM(LLM):
    """Stand-in for `api.llm.LLM` — returns whatever JSON the test sets up.

    Parameters
    ----------
    payload:
        Dict passed to ``output_model.model_validate(payload)`` and returned
        from ``complete_structured``.  Required unless *raise_exc* or
        *should_not_be_called* is set.
    raise_exc:
        If provided, ``complete_structured`` raises this exception instead of
        returning a value.
    should_not_be_called:
        If True, ``complete_structured`` raises ``AssertionError`` — use this
        to prove a skill SHORT-CIRCUITS without ever touching the LLM
        (§11.1 conservatism rule).
    """

    def __init__(
        self,
        *,
        payload: dict[str, Any] | None = None,
        raise_exc: Exception | None = None,
        should_not_be_called: bool = False,
    ) -> None:
        # Skip parent __init__ — we don't want a real Anthropic client.
        self._client = None  # type: ignore[assignment]
        self._payload = payload
        self._raise = raise_exc
        self._should_not_be_called = should_not_be_called
        self.calls: list[dict[str, Any]] = []

    @property
    def call_count(self) -> int:
        """Number of times ``complete_structured`` was successfully invoked."""
        return len(self.calls)

    async def complete_structured(  # type: ignore[override]
        self,
        *,
        system: str,
        user: str,
        output_model: type[BaseModel],
        model: str | None = None,
        max_tokens: int = 4096,
        cache_system: bool = True,
    ) -> tuple[BaseModel, LLMMetrics]:
        if self._should_not_be_called:
            raise AssertionError(
                "LLM should not have been called (§11.1 short-circuit)"
            )
        self.calls.append({"system": system, "user": user, "model": model})
        if self._raise is not None:
            raise self._raise
        assert self._payload is not None, "FakeLLM needs payload or raise_exc"
        parsed = output_model.model_validate(self._payload)
        metrics = LLMMetrics(
            model=model or "claude-haiku-4-5-20251001",
            latency_ms=42,
            cost_usd=0.0001,
            input_tokens=1500,
            output_tokens=200,
        )
        return parsed, metrics
