from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GameStatus(StrEnum):
    PLAYING = "playing"
    WON = "won"
    LOST = "lost"


class Location(StrEnum):
    SILK_BOARD = "silk_board"
    MADIWALA = "madiwala"
    BTM_LAYOUT = "btm_layout"
    KORAMANGALA = "koramangala"
    MG_ROAD = "mg_road"
    HEBBAL = "hebbal"
    AIRPORT_ROAD = "airport_road"
    AIRPORT = "kempegowda_international_airport"


class ActionType(StrEnum):
    ASK_AUTO = "ask_auto"
    NEGOTIATE_AUTO = "negotiate_auto"
    REJECT_AUTO = "reject_auto"
    TAKE_BUS = "take_bus"
    CALL_FRIEND = "call_friend"
    TAKE_CAB = "take_cab"
    CHARGE_PHONE = "charge_phone"
    TRADE_SAMOSA = "trade_samosa"
    ASK_DIRECTIONS = "ask_directions"
    WALK = "walk"
    USE_METRO = "use_metro"
    INTERACT_WITH_NPC = "interact_with_npc"
    EXPLORE_LOCATION = "explore_location"
    UNKNOWN = "unknown"


class AvailableAction(BaseModel):
    action_id: ActionType
    label: str
    command: str
    description: str
    category: Literal["travel", "social", "resource", "exploration"]
    priority: int = Field(ge=0)
    target: Location | None = None
    enabled: bool = True
    disabled_reason: str | None = None
    minutes: int | None = Field(default=None, ge=0)
    cash_cost: int = Field(default=0, ge=0)
    battery_cost: int = Field(default=0, ge=0)


class WorldLocation(BaseModel):
    id: Location
    label: str
    description: str
    lane: Literal["main", "alternate"]
    order: int = Field(ge=0)
    progress: int = Field(ge=0, le=100)
    is_destination: bool = False


class WorldRoute(BaseModel):
    origin: Location
    destination: Location
    action_id: ActionType
    minutes: int = Field(ge=0)
    cash_cost: int = Field(ge=0)
    battery_cost: int = Field(ge=0)
    requirement: str | None = None


class WorldAction(BaseModel):
    id: ActionType
    label: str
    description: str
    category: Literal["travel", "social", "resource", "exploration"]
    priority: int = Field(ge=0)


class WorldDefinition(BaseModel):
    version: str
    locations: list[WorldLocation]
    routes: list[WorldRoute]
    actions: list[WorldAction]


class HistoryEntry(BaseModel):
    turn: int
    player_input: str
    action: str | None = None
    accepted: bool
    message: str
    time_before: int
    time_after: int
    cash_delta: int = 0
    battery_delta: int = 0


class GameState(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    session_id: str
    player_name: str
    current_time: int = Field(ge=0)
    checkin_deadline: int = Field(ge=0)
    flight_time: int = Field(ge=0)
    location: Location
    cash: int = Field(ge=0)
    battery: int = Field(ge=0, le=100)
    inventory: list[str]
    turn_count: int = Field(ge=0)
    status: GameStatus
    history: list[HistoryEntry]
    characters_met: list[str]
    character_memory: dict[str, dict[str, Any]]
    discovered_locations: list[Location]
    narrative: str
    last_action: str | None = None
    random_seed: int


class ActionProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_type: ActionType
    target: str | None = Field(default=None, max_length=100)
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(min_length=1, max_length=240)


class InterpretationMetadata(BaseModel):
    source: Literal["gemini", "deterministic"] = "deterministic"
    attempts: int = Field(default=0, ge=0, le=3)
    fallback_reason: Literal[
        "not_configured", "invalid_response", "timeout", "provider_error", "low_confidence"
    ] | None = None


class NarrativeProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scene: str = Field(min_length=1, max_length=240)
    ravi_line: str = Field(min_length=1, max_length=180)

    @field_validator("scene", "ravi_line")
    @classmethod
    def one_line_text(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("narrative text cannot be blank")
        return value


class StateChanges(BaseModel):
    time_minutes: int = 0
    cash: int = 0
    battery: int = 0
    added_items: list[str] = Field(default_factory=list)
    removed_items: list[str] = Field(default_factory=list)
    location_from: Location | None = None
    location_to: Location | None = None


class ActionResult(BaseModel):
    accepted: bool
    message: str
    action: str | None
    changes: StateChanges
    state: GameState
    available_actions: list[AvailableAction]
    duplicate: bool = False
    interpretation: InterpretationMetadata = Field(default_factory=InterpretationMetadata)
    narration: InterpretationMetadata = Field(default_factory=InterpretationMetadata)


class NewGameRequest(BaseModel):
    player_name: str = Field(default="Traveller", min_length=1, max_length=40)
    random_seed: int | None = None

    @field_validator("player_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("player_name cannot be blank")
        return value


class GameContext(BaseModel):
    state: GameState
    available_actions: list[AvailableAction]


class ActionRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    player_input: str = Field(min_length=1, max_length=500)
    request_id: str = Field(min_length=1, max_length=100)

    @field_validator("session_id", "player_input", "request_id")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value cannot be blank")
        return value


class HealthResponse(BaseModel):
    status: str
    service: str

