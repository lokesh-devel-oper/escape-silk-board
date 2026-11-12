from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Protocol

from pydantic import ValidationError

from ..models import ActionProposal, ActionType, AvailableAction, GameState, InterpretationMetadata
from ..world import ACTION_ALIASES, resolve_location_target
from .prompts import INTENT_SYSTEM_PROMPT, build_intent_prompt


class ProposalClient(Protocol):
    async def propose(self, system_instruction: str, prompt: str) -> str: ...


@dataclass(frozen=True)
class InterpretationDecision:
    proposal: ActionProposal | None
    metadata: InterpretationMetadata


class DeterministicIntentInterpreter:
    """Keyword fallback that proposes actions but never mutates state."""

    def interpret(self, player_input: str) -> ActionProposal | None:
        normalized = re.sub(r"[^a-z0-9\s]", " ", player_input.casefold())
        normalized = " ".join(normalized.split())
        matches: list[tuple[int, str, str]] = []
        for action, aliases in ACTION_ALIASES.items():
            for alias in aliases:
                if re.search(rf"\b{re.escape(alias)}\b", normalized):
                    matches.append((len(alias), action, alias))
        if not matches:
            return None
        _, action, alias = max(matches)
        destination_match = re.search(r"\b(?:to|toward|towards|for)\s+(?:the\s+)?(.+)$", normalized)
        destination = resolve_location_target(destination_match.group(1)) if destination_match else None
        return ActionProposal(
            action_type=ActionType(action),
            target=destination.value if destination else None,
            confidence=0.75,
            reason=f"Matched the supported phrase '{alias}'.",
        )


class IntentInterpreter:
    def __init__(
        self,
        gemini_client: ProposalClient | None = None,
        *,
        timeout_seconds: float = 5.0,
        max_retries: int = 1,
        minimum_confidence: float = 0.55,
        fallback: DeterministicIntentInterpreter | None = None,
    ) -> None:
        self.gemini_client = gemini_client
        self.timeout_seconds = max(0.01, min(timeout_seconds, 30.0))
        self.max_retries = max(0, min(max_retries, 2))
        self.minimum_confidence = max(0.0, min(minimum_confidence, 1.0))
        self.fallback = fallback or DeterministicIntentInterpreter()

    async def interpret(
        self,
        player_input: str,
        state: GameState,
        available_actions: list[AvailableAction | str],
    ) -> InterpretationDecision:
        if self.gemini_client is None:
            return self._fallback(player_input, 0, "not_configured")

        prompt = build_intent_prompt(player_input, state, available_actions)
        last_reason = "provider_error"
        attempts = 0
        for attempts in range(1, self.max_retries + 2):
            try:
                raw = await asyncio.wait_for(
                    self.gemini_client.propose(INTENT_SYSTEM_PROMPT, prompt),
                    timeout=self.timeout_seconds,
                )
                proposal = ActionProposal.model_validate_json(raw)
                if proposal.confidence < self.minimum_confidence:
                    return self._fallback(player_input, attempts, "low_confidence")
                return InterpretationDecision(
                    proposal=proposal,
                    metadata=InterpretationMetadata(source="gemini", attempts=attempts),
                )
            except asyncio.TimeoutError:
                last_reason = "timeout"
            except (ValidationError, ValueError, TypeError):
                last_reason = "invalid_response"
            except Exception:
                last_reason = "provider_error"

        return self._fallback(player_input, attempts, last_reason)

    def _fallback(self, player_input: str, attempts: int, reason: str) -> InterpretationDecision:
        return InterpretationDecision(
            proposal=self.fallback.interpret(player_input),
            metadata=InterpretationMetadata(
                source="deterministic",
                attempts=attempts,
                fallback_reason=reason,
            ),
        )

