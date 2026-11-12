from __future__ import annotations

import asyncio

from .ai.interpreter import IntentInterpreter
from .ai.narrator import NarrativeGenerator
from .engine import GameEngine
from .models import ActionResult, GameState, GameStatus


class SessionNotFoundError(KeyError):
    pass


class IdempotencyConflictError(ValueError):
    pass


class InMemorySessionStore:
    """Single-process session store with per-session serialization and idempotency."""

    def __init__(
        self,
        engine: GameEngine | None = None,
        intent_interpreter: IntentInterpreter | None = None,
        narrative_generator: NarrativeGenerator | None = None,
    ) -> None:
        self.engine = engine or GameEngine()
        self.intent_interpreter = intent_interpreter or IntentInterpreter()
        self.narrative_generator = narrative_generator or NarrativeGenerator()
        self._states: dict[str, GameState] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._results: dict[str, dict[str, ActionResult]] = {}
        self._request_inputs: dict[str, dict[str, str]] = {}
        self._index_lock = asyncio.Lock()

    async def create(self, player_name: str, random_seed: int | None = None) -> GameState:
        state = self.engine.new_game(player_name, random_seed)
        async with self._index_lock:
            self._states[state.session_id] = state
            self._locks[state.session_id] = asyncio.Lock()
            self._results[state.session_id] = {}
            self._request_inputs[state.session_id] = {}
        return state.model_copy(deep=True)

    async def get(self, session_id: str) -> GameState:
        lock = await self._get_lock(session_id)
        async with lock:
            return self._states[session_id].model_copy(deep=True)

    async def process(self, session_id: str, player_input: str, request_id: str) -> ActionResult:
        lock = await self._get_lock(session_id)
        async with lock:
            cached = self._results[session_id].get(request_id)
            if cached is not None:
                if self._request_inputs[session_id][request_id] != player_input:
                    raise IdempotencyConflictError(
                        "request_id was already used with different player input"
                    )
                duplicate = cached.model_copy(deep=True)
                duplicate.duplicate = True
                return duplicate

            state = self._states[session_id]
            if state.status == GameStatus.PLAYING:
                decision = await self.intent_interpreter.interpret(
                    player_input,
                    state.model_copy(deep=True),
                    self.engine.available_actions(state),
                )
                result = self.engine.process_proposal(state, player_input, decision.proposal)
                result.interpretation = decision.metadata
                deterministic_outcome = result.message
                narrative = await self.narrative_generator.generate(
                    player_input,
                    result.model_copy(deep=True),
                    deterministic_outcome,
                )
                result.message = narrative.text
                result.state.narrative = narrative.text
                if result.state.history:
                    result.state.history[-1].message = narrative.text
                result.narration = narrative.metadata
            else:
                result = self.engine.process_proposal(state, player_input, None)
            self._states[session_id] = result.state.model_copy(deep=True)
            self._results[session_id][request_id] = result.model_copy(deep=True)
            self._request_inputs[session_id][request_id] = player_input
            return result.model_copy(deep=True)

    async def reset(self, session_id: str) -> GameState:
        lock = await self._get_lock(session_id)
        async with lock:
            old = self._states[session_id]
            state = self.engine.new_game(old.player_name, old.random_seed, session_id=session_id)
            self._states[session_id] = state
            self._results[session_id] = {}
            self._request_inputs[session_id] = {}
            return state.model_copy(deep=True)

    async def _get_lock(self, session_id: str) -> asyncio.Lock:
        async with self._index_lock:
            lock = self._locks.get(session_id)
        if lock is None:
            raise SessionNotFoundError(session_id)
        return lock

