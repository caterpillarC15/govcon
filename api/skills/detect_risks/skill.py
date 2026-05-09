"""detect_risks — A7 stub.

§5.8 risk taxonomy + severity calibration + human-review enforcement.
Implementation will land in T2.4.
"""
from __future__ import annotations

from api.llm import LLMMetrics


async def detect_risks(payload: dict, *, llm) -> tuple[dict, LLMMetrics]:
    raise NotImplementedError("detect_risks will be implemented in T2.4")
