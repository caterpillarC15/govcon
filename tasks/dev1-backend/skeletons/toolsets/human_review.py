"""human_review toolset — escalation gate. Available to all agents.

When an agent encounters genuine ambiguity it cannot resolve (low extraction
confidence after retries, missing data, contradictory inputs), it escalates
via request_human_review. The agent run pauses and surfaces the question
to the user.

Hermes may have a built-in equivalent; check during A9 spike. If it does,
delete this stub and use the built-in.
"""
from __future__ import annotations


async def request_human_review(question: str, context: dict) -> None:
    """Halt the agent run and surface a question to the user.

    Args:
        question: concrete, specific question (not "I don't know what to do").
                  Example: "Solicitation requires CMMC Level 3; profile lists
                  CMMC Level 2. Treat as eligibility blocker (reject) or
                  capability gap (lower fit score)?"
        context: free-form dict; surfaced to the user with the question.

    Effect:
        - Emits a `needs_human` trace event (CONTRACTS.md §3).
        - Sets agent_run.status = "needs_human" in DB.
        - Frontend renders a modal with the question + Resume / Cancel buttons.

    No return value — the run halts; resumption is a user-initiated event.

    Cost: $0 (no LLM call).
    """
    raise NotImplementedError(
        "A9 — Dev 1 implements as part of Hermes integration. "
        "May be replaceable by a Hermes built-in; confirm during the spike."
    )
