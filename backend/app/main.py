from __future__ import annotations

import os

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .ai.client import GeminiIntentClient, GeminiNarrativeClient
from .ai.interpreter import IntentInterpreter
from .ai.narrator import NarrativeGenerator
from .config import AISettings
from .models import (
    ActionRequest,
    ActionResult,
    GameContext,
    GameState,
    HealthResponse,
    NewGameRequest,
    WorldDefinition,
)
from .store import IdempotencyConflictError, InMemorySessionStore, SessionNotFoundError
from .world import build_world_definition


def _allowed_origins() -> list[str]:
    configured = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    return [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]


def _production_store() -> InMemorySessionStore:
    settings = AISettings.from_env()
    intent_client = None
    narrative_client = None
    if settings.configured:
        try:
            intent_client = GeminiIntentClient(
                api_key=settings.api_key or "",
                model=settings.model or "",
                timeout_seconds=settings.timeout_seconds,
            )
            narrative_client = GeminiNarrativeClient(
                api_key=settings.api_key or "",
                model=settings.model or "",
                timeout_seconds=settings.timeout_seconds,
            )
        except RuntimeError:
            # A missing optional SDK must not make the deterministic game unavailable.
            intent_client = None
            narrative_client = None
    interpreter = IntentInterpreter(
        intent_client,
        timeout_seconds=settings.timeout_seconds,
        max_retries=settings.max_retries,
        minimum_confidence=settings.minimum_confidence,
    )
    narrator = NarrativeGenerator(
        narrative_client,
        timeout_seconds=settings.timeout_seconds,
        max_retries=settings.max_retries,
    )
    return InMemorySessionStore(
        intent_interpreter=interpreter,
        narrative_generator=narrator,
    )


def create_app(store: InMemorySessionStore | None = None) -> FastAPI:
    app = FastAPI(
        title="Escape Silk Board API",
        version="0.1.0",
        description="Deterministic game API for Escape Silk Board.",
    )
    app.state.session_store = store or _production_store()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(SessionNotFoundError)
    async def session_not_found(_: Request, exc: SessionNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": f"Game session '{exc.args[0]}' was not found."},
        )

    @app.exception_handler(IdempotencyConflictError)
    async def idempotency_conflict(_: Request, exc: IdempotencyConflictError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(exc)},
        )

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", service="escape-silk-board-api")

    @app.get("/api/world", response_model=WorldDefinition)
    async def world() -> WorldDefinition:
        return build_world_definition()

    @app.post("/api/game/new", response_model=GameState, status_code=status.HTTP_201_CREATED)
    async def new_game(request: NewGameRequest) -> GameState:
        return await app.state.session_store.create(request.player_name, request.random_seed)

    @app.post("/api/game/action", response_model=ActionResult)
    async def perform_action(request: ActionRequest) -> ActionResult:
        return await app.state.session_store.process(
            request.session_id, request.player_input.strip(), request.request_id
        )

    @app.get("/api/game/state/{session_id}", response_model=GameState)
    async def game_state(session_id: str) -> GameState:
        return await app.state.session_store.get(session_id)

    @app.get("/api/game/context/{session_id}", response_model=GameContext)
    async def game_context(session_id: str) -> GameContext:
        state = await app.state.session_store.get(session_id)
        return GameContext(
            state=state,
            available_actions=app.state.session_store.engine.available_actions(state),
        )

    @app.post("/api/game/reset/{session_id}", response_model=GameState)
    async def reset_game(session_id: str) -> GameState:
        return await app.state.session_store.reset(session_id)

    return app


app = create_app()

