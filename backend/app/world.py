from __future__ import annotations

import re
from dataclasses import dataclass

from .models import (
    ActionType,
    Location,
    WorldAction,
    WorldDefinition,
    WorldLocation,
    WorldRoute,
)


@dataclass(frozen=True)
class LocationDefinition:
    name: str
    description: str
    npcs: tuple[str, ...]
    connected_locations: tuple[Location, ...]


@dataclass(frozen=True)
class Route:
    origin: Location
    destination: Location
    action: str
    minutes: int
    cash_cost: int = 0
    battery_cost: int = 0
    requirement: str | None = None
    possible_events: tuple["TravelEvent", ...] = ()


@dataclass(frozen=True)
class TravelEvent:
    identifier: str
    extra_minutes: int
    narrative: str


@dataclass(frozen=True)
class ActionDefinition:
    identifier: str
    aliases: tuple[str, ...]
    narrative_context: str
    base_minutes: int | None = None
    cash_delta: int = 0
    battery_delta: int = 0
    preconditions: tuple[str, ...] = ()
    possible_events: tuple[str, ...] = ()


@dataclass(frozen=True)
class LocationPresentation:
    label: str
    lane: str
    order: int
    progress: int


@dataclass(frozen=True)
class ActionPresentation:
    label: str
    category: str
    priority: int


LOCATIONS: dict[Location, LocationDefinition] = {
    Location.SILK_BOARD: LocationDefinition(
        "Silk Board Junction",
        "A sea of brake lights, horns, and heroic optimism.",
        ("ravi", "auto_driver_01", "tea_vendor"),
        (Location.BTM_LAYOUT, Location.MADIWALA, Location.HEBBAL, Location.AIRPORT),
    ),
    Location.MADIWALA: LocationDefinition(
        "Madiwala", "Crowded streets offer several ways north.", ("bus_conductor",),
        (Location.SILK_BOARD, Location.KORAMANGALA),
    ),
    Location.BTM_LAYOUT: LocationDefinition(
        "BTM Layout", "Side streets trade gridlock for confusing turns.", ("shopkeeper",),
        (Location.SILK_BOARD, Location.KORAMANGALA),
    ),
    Location.KORAMANGALA: LocationDefinition(
        "Koramangala", "Cafes glow while traffic quietly plots against you.", ("friend_ananya",),
        (Location.BTM_LAYOUT, Location.MADIWALA, Location.MG_ROAD),
    ),
    Location.MG_ROAD: LocationDefinition(
        "MG Road", "The metro concourse is busy but moving.", ("metro_guard",),
        (Location.KORAMANGALA, Location.HEBBAL),
    ),
    Location.HEBBAL: LocationDefinition(
        "Hebbal", "The flyover points toward the airport and the clock feels louder.",
        ("airport_bus_conductor",), (Location.MG_ROAD, Location.AIRPORT_ROAD, Location.AIRPORT),
    ),
    Location.AIRPORT_ROAD: LocationDefinition(
        "Airport Road", "The terminal signs are finally visible.", ("cab_driver_02",),
        (Location.HEBBAL, Location.AIRPORT),
    ),
    Location.AIRPORT: LocationDefinition(
        "Kempegowda International Airport", "The terminal doors are directly ahead.", (), (),
    ),
}


LOCATION_PRESENTATION: dict[Location, LocationPresentation] = {
    Location.SILK_BOARD: LocationPresentation("Silk Board", "main", 0, 4),
    Location.HEBBAL: LocationPresentation("Hebbal", "main", 1, 66),
    Location.AIRPORT_ROAD: LocationPresentation("Airport Road", "main", 2, 86),
    Location.AIRPORT: LocationPresentation("KIA Terminal", "main", 3, 100),
    Location.MADIWALA: LocationPresentation("Madiwala", "alternate", 0, 14),
    Location.BTM_LAYOUT: LocationPresentation("BTM Layout", "alternate", 1, 16),
    Location.KORAMANGALA: LocationPresentation("Koramangala", "alternate", 2, 28),
    Location.MG_ROAD: LocationPresentation("MG Road", "alternate", 3, 45),
}


LOCATION_ALIASES: dict[Location, tuple[str, ...]] = {
    Location.SILK_BOARD: ("silk board", "silk board junction"),
    Location.MADIWALA: ("madiwala",),
    Location.BTM_LAYOUT: ("btm", "btm layout"),
    Location.KORAMANGALA: ("koramangala",),
    Location.MG_ROAD: ("mg road", "mg"),
    Location.HEBBAL: ("hebbal",),
    Location.AIRPORT_ROAD: ("airport road",),
    Location.AIRPORT: ("airport", "kia", "terminal", "kempegowda international airport"),
}


BUS_EVENTS = (
    TravelEvent("green_signal", 0, "A rare chain of green signals earns Ravi's suspicious respect."),
    TravelEvent("signal_delay", 2, "One stubborn signal adds two minutes, but the route stays fair."),
)

CAB_EVENTS = (
    TravelEvent("steady_traffic", 0, "Traffic keeps moving—an event Ravi considers supernatural."),
    TravelEvent("brief_bottleneck", 2, "A brief bottleneck costs two minutes before the road opens."),
)


ROUTES: tuple[Route, ...] = (
    Route(Location.SILK_BOARD, Location.HEBBAL, "take_bus", 62, 50, possible_events=BUS_EVENTS),
    Route(Location.HEBBAL, Location.AIRPORT, "take_bus", 40, 60, possible_events=BUS_EVENTS),
    Route(
        Location.SILK_BOARD, Location.AIRPORT, "take_cab", 78, 450, 5,
        "negotiated_auto", CAB_EVENTS,
    ),
    Route(Location.KORAMANGALA, Location.AIRPORT, "take_cab", 60, 400, 5, possible_events=CAB_EVENTS),
    Route(Location.HEBBAL, Location.AIRPORT, "take_cab", 30, 280, 4, possible_events=CAB_EVENTS),
    Route(Location.AIRPORT_ROAD, Location.AIRPORT, "take_cab", 14, 150, 3),
    Route(Location.KORAMANGALA, Location.MG_ROAD, "use_metro", 18, 35, 1),
    Route(Location.MG_ROAD, Location.HEBBAL, "use_metro", 22, 45, 1),
    Route(Location.SILK_BOARD, Location.BTM_LAYOUT, "walk", 14),
    Route(Location.BTM_LAYOUT, Location.KORAMANGALA, "walk", 15),
    Route(Location.SILK_BOARD, Location.MADIWALA, "walk", 15),
    Route(Location.MADIWALA, Location.KORAMANGALA, "walk", 16),
    Route(Location.HEBBAL, Location.AIRPORT_ROAD, "walk", 30),
    Route(Location.AIRPORT_ROAD, Location.AIRPORT, "walk", 20),
)


ACTION_REGISTRY: dict[str, ActionDefinition] = {
    definition.identifier: definition
    for definition in (
        ActionDefinition("negotiate_auto", ("negotiate", "bargain", "lower the auto", "reduce the fare"), "Negotiate a known driver's offer.", 3, preconditions=("auto_driver_met", "offer_active")),
        ActionDefinition("reject_auto", ("reject auto", "refuse auto", "walk away", "no deal"), "Reject a known driver's offer.", 1, preconditions=("auto_driver_met", "offer_active")),
        ActionDefinition("ask_auto", ("find an auto", "ask auto", "auto rickshaw", "get an auto", "auto"), "Find and receive an auto offer.", 2, preconditions=("at_silk_board",)),
        ActionDefinition("take_bus", ("take a bus", "take bus", "airport bus", "catch a bus", "bus"), "Travel on a valid bus route.", preconditions=("valid_route",), possible_events=("green_signal", "signal_delay")),
        ActionDefinition("call_friend", ("call a friend", "phone a friend", "call my friend", "ring a friend"), "Call Ananya for route advice.", 5, battery_delta=-5, preconditions=("battery_at_least_5",)),
        ActionDefinition("take_cab", ("book an uber", "book a cab", "take a cab", "take taxi", "uber", "cab", "taxi"), "Travel on a valid cab route.", preconditions=("valid_route", "sufficient_cash", "sufficient_battery"), possible_events=("steady_traffic", "brief_bottleneck")),
        ActionDefinition("charge_phone", ("charge my phone", "charge phone", "charging", "charger"), "Buy time at a safe charging point.", 15, cash_delta=-20, battery_delta=25, preconditions=("at_charging_point", "cash_at_least_20", "battery_below_100")),
        ActionDefinition("trade_samosa", ("trade the samosa", "sell the samosa", "trade samosa", "sell samosa"), "Trade the inventory item once.", 3, cash_delta=30, preconditions=("at_silk_board", "has_cold_samosa")),
        ActionDefinition("ask_directions", ("ask for directions", "ask directions", "directions", "which way"), "Receive a contextual route hint.", 3),
        ActionDefinition("use_metro", ("take the metro", "use metro", "catch metro", "metro"), "Travel on a valid metro route.", preconditions=("valid_route", "sufficient_cash")),
        ActionDefinition("interact_with_npc", ("talk to ravi", "speak to ravi", "talk to", "speak to", "chat"), "Talk to a local character.", 2),
        ActionDefinition("explore_location", ("look around", "explore", "inspect", "search nearby"), "Inspect the current location.", 4),
        ActionDefinition("walk", ("walk", "go on foot", "start walking"), "Walk along a connected route.", preconditions=("valid_route",)),
    )
}

ACTION_ALIASES = {identifier: definition.aliases for identifier, definition in ACTION_REGISTRY.items()}


ACTION_PRESENTATION: dict[str, ActionPresentation] = {
    "take_bus": ActionPresentation("Take the bus", "travel", 10),
    "take_cab": ActionPresentation("Book a cab", "travel", 20),
    "use_metro": ActionPresentation("Take the metro", "travel", 30),
    "walk": ActionPresentation("Walk", "travel", 40),
    "ask_auto": ActionPresentation("Find an auto", "social", 50),
    "negotiate_auto": ActionPresentation("Negotiate the fare", "social", 60),
    "charge_phone": ActionPresentation("Charge the phone", "resource", 70),
    "trade_samosa": ActionPresentation("Trade the samosa", "resource", 80),
    "call_friend": ActionPresentation("Call a friend", "social", 90),
    "ask_directions": ActionPresentation("Ask for directions", "exploration", 100),
    "interact_with_npc": ActionPresentation("Talk to Ravi", "social", 110),
    "explore_location": ActionPresentation("Look around", "exploration", 120),
    "reject_auto": ActionPresentation("Reject the auto", "social", 130),
}


def resolve_location_target(value: str | None) -> Location | None:
    if not value:
        return None
    normalized = " ".join(re.sub(r"[^a-z0-9\s]", " ", value.casefold()).split())
    for location, aliases in LOCATION_ALIASES.items():
        if normalized == location.value.replace("_", " ") or any(
            re.search(rf"\b{re.escape(alias)}\b", normalized) for alias in aliases
        ):
            return location
    return None


def build_world_definition() -> WorldDefinition:
    locations = [
        WorldLocation(
            id=location,
            label=LOCATION_PRESENTATION[location].label,
            description=definition.description,
            lane=LOCATION_PRESENTATION[location].lane,
            order=LOCATION_PRESENTATION[location].order,
            progress=LOCATION_PRESENTATION[location].progress,
            is_destination=location == Location.AIRPORT,
        )
        for location, definition in LOCATIONS.items()
    ]
    routes = [
        WorldRoute(
            origin=route.origin,
            destination=route.destination,
            action_id=ActionType(route.action),
            minutes=route.minutes,
            cash_cost=route.cash_cost,
            battery_cost=route.battery_cost,
            requirement=route.requirement,
        )
        for route in ROUTES
    ]
    actions = [
        WorldAction(
            id=ActionType(identifier),
            label=ACTION_PRESENTATION[identifier].label,
            description=definition.narrative_context,
            category=ACTION_PRESENTATION[identifier].category,
            priority=ACTION_PRESENTATION[identifier].priority,
        )
        for identifier, definition in ACTION_REGISTRY.items()
    ]
    return WorldDefinition(
        version="1.0",
        locations=sorted(locations, key=lambda item: (item.lane, item.order)),
        routes=routes,
        actions=sorted(actions, key=lambda item: item.priority),
    )

