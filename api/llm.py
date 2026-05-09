"""Anthropic SDK wrapper with structured-output, prompt caching, and cost tracking.

Used by every LLM-backed skill (A5 extract_requirements, A6 score_fit rationale,
A7 detect_risks, A8 generate_action_package). The skill knows what it wants
back; this layer handles the SDK plumbing (auth, retries, JSON-schema-enforced
output, cost math, cache-hit accounting).

Per CONTRACTS.md §5, every tool reports `latency_ms` and `cost_usd`. Skills
get those from `LLMMetrics` and forward them to the trace bridge.
"""
from __future__ import annotations

import logging
import time
from typing import Any, TypeVar

from anthropic import AsyncAnthropic
from pydantic import BaseModel, Field

from api.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Approximate per-million-token rates (USD) — adjust to match current pricing.
# Cache reads: ~0.1× input rate. Cache writes: ~1.25× input rate (5-min TTL).
_PRICING_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-haiku-4-5-20251001": (1.0, 5.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-opus-4-6": (5.0, 25.0),
    "claude-opus-4-7": (5.0, 25.0),
}


def estimate_cost_usd(
    model: str,
    *,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_creation_tokens: int = 0,
) -> float:
    in_rate, out_rate = _PRICING_PER_MTOK.get(model, (3.0, 15.0))
    base = (input_tokens * in_rate + output_tokens * out_rate) / 1_000_000
    cache_read = cache_read_tokens * in_rate * 0.1 / 1_000_000
    cache_write = cache_creation_tokens * in_rate * 1.25 / 1_000_000
    return round(base + cache_read + cache_write, 6)


class LLMMetrics(BaseModel):
    model: str
    latency_ms: int = Field(..., ge=0)
    cost_usd: float = Field(..., ge=0)
    input_tokens: int = Field(0, ge=0)
    output_tokens: int = Field(0, ge=0)
    cache_read_tokens: int = Field(0, ge=0)
    cache_creation_tokens: int = Field(0, ge=0)
    attempts: int = Field(1, ge=0)


class LLMError(Exception):
    """Skill-facing error wrapping any unrecoverable Anthropic SDK failure."""


class LLM:
    """Thin async wrapper. Skills hold one instance; tests inject a fake."""

    def __init__(self, client: AsyncAnthropic | None = None) -> None:
        self._client = client or AsyncAnthropic(api_key=settings.anthropic_api_key)

    @property
    def raw(self) -> AsyncAnthropic:
        return self._client

    async def complete_structured(
        self,
        *,
        system: str,
        user: str,
        output_model: type[T],
        model: str | None = None,
        max_tokens: int = 4096,
        cache_system: bool = True,
    ) -> tuple[T, LLMMetrics]:
        """Run a one-shot completion and parse the response into `output_model`.

        Uses Anthropic's `output_config.format` so the API enforces the JSON shape
        (no parse-and-retry loop needed). Sets a top-level cache_control breakpoint
        on the system prompt when `cache_system` so identical system text is reused
        across calls (5-min TTL).
        """
        model_id = model or settings.llm_dev_model
        schema = output_model.model_json_schema()

        kwargs: dict[str, Any] = {
            "model": model_id,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "output_config": {"format": {"type": "json_schema", "schema": schema}},
        }
        if cache_system:
            kwargs["cache_control"] = {"type": "ephemeral"}

        t0 = time.monotonic()
        try:
            response = await self._client.messages.create(**kwargs)
        except Exception as exc:  # noqa: BLE001 -- normalize SDK errors at the boundary
            raise LLMError(f"Anthropic call failed for model={model_id}: {exc}") from exc
        latency_ms = int((time.monotonic() - t0) * 1000)

        text = next((b.text for b in response.content if getattr(b, "type", None) == "text"), None)
        if text is None:
            raise LLMError(f"No text block in response (stop_reason={response.stop_reason})")

        try:
            parsed = output_model.model_validate_json(text)
        except Exception as exc:  # noqa: BLE001
            logger.error("Structured-output parse failed for %s: %s\nraw=%r", model_id, exc, text[:1000])
            raise LLMError(f"output_model={output_model.__name__} parse failed: {exc}") from exc

        usage = response.usage
        cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
        cache_create = getattr(usage, "cache_creation_input_tokens", 0) or 0
        cost = estimate_cost_usd(
            model_id,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_read_tokens=cache_read,
            cache_creation_tokens=cache_create,
        )

        metrics = LLMMetrics(
            model=model_id,
            latency_ms=latency_ms,
            cost_usd=cost,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_read_tokens=cache_read,
            cache_creation_tokens=cache_create,
        )
        return parsed, metrics
