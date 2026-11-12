from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Protocol

from pydantic import ValidationError

from ..models import (
    ActionResult,
    GameStatus,
    InterpretationMetadata,
    NarrativeProposal,
)
from ..world import LOCATIONS
from .prompts import NARRATIVE_SYSTEM_PROMPT, build_narrative_prompt


class NarrativeClient(Protocol):
    async def narrate(self, system_instruction: str, prompt: str) -> str: ...


@dataclass(frozen=True)
class NarrativeDecision:
    text: str
    metadata: InterpretationMetadata


class NarrativeGuard:
    """Rejects model prose that tries to restate authoritative game facts."""

    _forbidden_facts = re.compile(
        r"(?:\d|₹|%|\b(?:cash|money|rupees?|battery|inventory|minutes?|hours?|"
        r"paid|spent|earned|gained|sold|traded|charged|boarded|arrived|reached|"
        r"check[ -]?in|flight|won|win|lost|lose|deadline)\b)",
        re.IGNORECASE,
    )

    @classmethod
    def validate(cls, proposal: NarrativeProposal, result: ActionResult) -> None:
        combined = f"{proposal.scene} {proposal.ravi_line}"
        if cls._forbidden_facts.search(combined):
            raise ValueError("Narrative attempted to restate authoritative facts")

        if any(len(re.findall(r"[.!?]+", text)) != 1 for text in (proposal.scene, proposal.ravi_line)):
            raise ValueError("Scene and Ravi line must each be one sentence")

        lowered = combined.casefold().replace("_", " ")
        current = result.state.location
        for location, definition in LOCATIONS.items():
            if location == current:
                continue
            names = {location.value.replace("_", " "), definition.name.casefold()}
            if any(name in lowered for name in names):
                raise ValueError("Narrative mentioned a non-current location")

        prior_messages = [entry.message.casefold() for entry in result.state.history[:-1]]
        if any(
            proposal.scene.casefold() in message or proposal.ravi_line.casefold() in message
            for message in prior_messages
        ):
            raise ValueError("Narrative repeated a recent line")


class DeterministicNarrator:
    def narrate(self, result: ActionResult, deterministic_outcome: str) -> str:
        if result.state.status == GameStatus.WON:
            return deterministic_outcome
        if result.state.status == GameStatus.LOST:
            return deterministic_outcome

        remaining = result.state.checkin_deadline - result.state.current_time
        if remaining <= 20 and "Ravi" not in deterministic_outcome:
            return deterministic_outcome + " Ravi's jokes shorten as the deadline gets uncomfortably close."
        return deterministic_outcome


class NarrativeGenerator:
    def __init__(
        self,
        gemini_client: NarrativeClient | None = None,
        *,
        timeout_seconds: float = 5.0,
        max_retries: int = 1,
        fallback: DeterministicNarrator | None = None,
    ) -> None:
        self.gemini_client = gemini_client
        self.timeout_seconds = max(0.01, min(timeout_seconds, 30.0))
        self.max_retries = max(0, min(max_retries, 2))
        self.fallback = fallback or DeterministicNarrator()

    async def generate(
        self,
        player_input: str,
        result: ActionResult,
        deterministic_outcome: str,
    ) -> NarrativeDecision:
        if self.gemini_client is None:
            return self._fallback(result, deterministic_outcome, 0, "not_configured")

        prompt = build_narrative_prompt(player_input, result, deterministic_outcome)
        last_reason = "provider_error"
        attempts = 0
        for attempts in range(1, self.max_retries + 2):
            try:
                raw = await asyncio.wait_for(
                    self.gemini_client.narrate(NARRATIVE_SYSTEM_PROMPT, prompt),
                    timeout=self.timeout_seconds,
                )
                proposal = NarrativeProposal.model_validate_json(raw)
                NarrativeGuard.validate(proposal, result)
                line = proposal.ravi_line.strip('"“”')
                text = f"{deterministic_outcome} {proposal.scene} Ravi adds, “{line}”"
                return NarrativeDecision(
                    text=text,
                    metadata=InterpretationMetadata(source="gemini", attempts=attempts),
                )
            except asyncio.TimeoutError:
                last_reason = "timeout"
            except (ValidationError, ValueError, TypeError):
                last_reason = "invalid_response"
            except Exception:
                last_reason = "provider_error"

        return self._fallback(result, deterministic_outcome, attempts, last_reason)

    def _fallback(
        self,
        result: ActionResult,
        deterministic_outcome: str,
        attempts: int,
        reason: str,
    ) -> NarrativeDecision:
        return NarrativeDecision(
            text=self.fallback.narrate(result, deterministic_outcome),
            metadata=InterpretationMetadata(
                source="deterministic",
                attempts=attempts,
                fallback_reason=reason,
            ),
        )

