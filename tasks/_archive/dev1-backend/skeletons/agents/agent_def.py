"""Shared AgentDef structure consumed by the Hermes runner."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


Role = Literal["orchestrator", "leaf"]


@dataclass(frozen=True)
class AgentDef:
    """Bundle of metadata used to construct a Hermes delegate_task() call.

    Attributes:
        role_id: stable identifier ("capture_lead", "compliance_officer", ...)
        role: Hermes delegation role — "orchestrator" allows nested delegation,
              "leaf" cannot delegate further (cap at max_spawn_depth).
        toolsets: tuple of toolset names this agent has access to. Hermes restricts
              tool calls to these via delegate_task(toolsets=[...]).
        instructions_path: path to the markdown file with the role-specific prompt
              (lives in tasks/dev1-backend/prompts/agent_<role>.md).
        persona_excerpt: short voice/disposition summary; used in trace events.
        skills_loaded_on_demand: tuple of SKILL.md skill names this agent typically
              consults. Listed for traceability; Hermes auto-loads on demand.
        default_model: optional model override for delegate_task. None = inherit
              from parent / config.yaml.
    """
    role_id: str
    role: Role
    toolsets: tuple[str, ...]
    instructions_path: Path
    persona_excerpt: str
    skills_loaded_on_demand: tuple[str, ...] = field(default_factory=tuple)
    default_model: str | None = None

    def load_instructions(self) -> str:
        """Read the role-specific prompt from disk."""
        return self.instructions_path.read_text()

    def to_delegate_kwargs(self, *, goal: str, context: object) -> dict:
        """Build kwargs for hermes.delegate_task() (or the parallel tasks=[] form).

        The runner passes:
            goal: high-level task statement
            context: rich context dict (opportunity, profile, parsed_chunks, etc.)

        It returns the structure Hermes expects.
        """
        kwargs: dict = {
            "goal": goal,
            "role": self.role,
            "toolsets": list(self.toolsets),
            "context": context,
        }
        # The actual instructions text is concatenated into context or system
        # prompt by the runner — implementation varies by Hermes invocation
        # mode (subprocess vs SDK). See /api/agent/hermes_runner.py (A9).
        if self.default_model:
            kwargs["model"] = self.default_model
        return kwargs
