from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass

from .models import (
    ActionProposal,
    ActionResult,
    ActionType,
    AvailableAction,
    GameState,
    GameStatus,
    HistoryEntry,
    Location,
    StateChanges,
)
from .ai.interpreter import DeterministicIntentInterpreter
from .world import (
    ACTION_PRESENTATION,
    ACTION_REGISTRY,
    LOCATION_PRESENTATION,
    LOCATIONS,
    ROUTES,
    Route,
    resolve_location_target,
)


INITIAL_TIME = 19 * 60
CHECKIN_DEADLINE = 20 * 60 + 55
FLIGHT_TIME = 21 * 60 + 40


class RuleViolation(Exception):
    """A safe, player-facing rejection raised by a game rule."""


@dataclass
class Transition:
    minutes: int
    message: str
    cash_delta: int = 0
    battery_delta: int = 0
    destination: Location | None = None
    add_items: tuple[str, ...] = ()
    remove_items: tuple[str, ...] = ()


class GameEngine:
    def __init__(self, interpreter: DeterministicIntentInterpreter | None = None) -> None:
        self.interpreter = interpreter or DeterministicIntentInterpreter()

    def new_game(
        self, player_name: str = "Traveller", random_seed: int | None = None, session_id: str | None = None
    ) -> GameState:
        session_id = session_id or str(uuid.uuid4())
        if random_seed is None:
            random_seed = int.from_bytes(hashlib.sha256(session_id.encode()).digest()[:4], "big")
        return GameState(
            session_id=session_id,
            player_name=player_name,
            current_time=INITIAL_TIME,
            checkin_deadline=CHECKIN_DEADLINE,
            flight_time=FLIGHT_TIME,
            location=Location.SILK_BOARD,
            cash=500,
            battery=32,
            inventory=["cold_samosa"],
            turn_count=0,
            status=GameStatus.PLAYING,
            history=[],
            characters_met=["ravi"],
            character_memory={"ravi": {"met": True, "relationship": "helpful", "warnings": 0}},
            discovered_locations=[Location.SILK_BOARD],
            narrative=(
                "Ravi points at the motionless traffic. “Welcome to Silk Board at 7 PM. "
                "Your check-in closes at 8:55, so perhaps start panicking efficiently, maga.”"
            ),
            random_seed=random_seed,
        )

    def available_actions(self, state: GameState) -> list[AvailableAction]:
        if state.status != GameStatus.PLAYING:
            return []
        options: list[AvailableAction] = []
        negotiated = bool(
            state.character_memory.get("auto_driver_01", {}).get("negotiated")
        )
        for route in ROUTES:
            if route.origin != state.location:
                continue
            if route.requirement == "negotiated_auto" and not negotiated:
                continue
            reason = None
            if state.cash < route.cash_cost:
                reason = f"Needs ₹{route.cash_cost}; you have ₹{state.cash}."
            elif state.battery < route.battery_cost:
                reason = f"Needs {route.battery_cost}% phone battery."
            presentation = ACTION_PRESENTATION[route.action]
            destination = LOCATION_PRESENTATION[route.destination].label
            label = f"{presentation.label} to {destination}"
            options.append(AvailableAction(
                action_id=ActionType(route.action),
                label=label,
                command=label,
                description=ACTION_REGISTRY[route.action].narrative_context,
                category=presentation.category,
                priority=presentation.priority,
                target=route.destination,
                enabled=reason is None,
                disabled_reason=reason,
                minutes=route.minutes,
                cash_cost=route.cash_cost,
                battery_cost=route.battery_cost,
            ))

        for action in ("ask_directions", "explore_location", "interact_with_npc"):
            options.append(self._action_option(action))
        if state.location == Location.SILK_BOARD:
            options.append(self._action_option("ask_auto"))
            charge_reason = None
            if state.cash < 20:
                charge_reason = "Needs ₹20."
            elif state.battery >= 100:
                charge_reason = "Phone is already fully charged."
            options.append(self._action_option("charge_phone", disabled_reason=charge_reason))
            if "cold_samosa" in state.inventory:
                options.append(self._action_option("trade_samosa"))
        auto_memory = state.character_memory.get("auto_driver_01", {})
        if (
            auto_memory.get("met")
            and not auto_memory.get("player_rejected")
            and not auto_memory.get("negotiated")
        ):
            options.extend((
                self._action_option("negotiate_auto"),
                self._action_option("reject_auto"),
            ))
        options.append(self._action_option(
            "call_friend",
            disabled_reason=None if state.battery >= 5 else "Needs at least 5% phone battery.",
        ))
        return sorted(options, key=lambda option: (option.priority, option.label))

    @staticmethod
    def _action_option(action: str, disabled_reason: str | None = None) -> AvailableAction:
        presentation = ACTION_PRESENTATION[action]
        definition = ACTION_REGISTRY[action]
        return AvailableAction(
            action_id=ActionType(action),
            label=presentation.label,
            command=presentation.label,
            description=definition.narrative_context,
            category=presentation.category,
            priority=presentation.priority,
            enabled=disabled_reason is None,
            disabled_reason=disabled_reason,
            minutes=definition.base_minutes,
            cash_cost=max(0, -definition.cash_delta),
            battery_cost=max(0, -definition.battery_delta),
        )

    def process(self, state: GameState, player_input: str) -> ActionResult:
        proposal = self.interpreter.interpret(player_input)
        return self.process_proposal(state, player_input, proposal)

    def process_proposal(
        self, state: GameState, player_input: str, proposal: ActionProposal | None
    ) -> ActionResult:
        if state.status != GameStatus.PLAYING:
            return self._rejected(state, player_input, None, "This game has already ended. Start a new game to continue.")

        if proposal is None or proposal.action_type == "unknown":
            return self._rejected(
                state, player_input, None,
                "Ravi squints. Try a concrete action such as finding an auto, taking a bus, walking, or asking directions.",
            )

        working = state.model_copy(deep=True)
        try:
            action = proposal.action_type.value
            transition = self._resolve(working, action, proposal.target)
            return self._apply(working, player_input, action, transition)
        except RuleViolation as exc:
            return self._rejected(state, player_input, proposal.action_type.value, str(exc))

    def _resolve(self, state: GameState, action: str, target: str | None = None) -> Transition:
        definition = ACTION_REGISTRY.get(action)
        if definition is None:
            raise RuleViolation("That action is not supported by the rules engine.")

        if action == "ask_auto":
            self._require(state.location == Location.SILK_BOARD, "There is no useful auto stand here.")
            memory = state.character_memory.setdefault("auto_driver_01", {})
            memory.update({"met": True, "last_offer": 900, "player_rejected": False, "relationship": "businesslike"})
            if "auto_driver_01" not in state.characters_met:
                state.characters_met.append("auto_driver_01")
            return Transition(definition.base_minutes or 0, "An auto driver quotes ₹900. Ravi whispers, “Airport alla, moon landing price.” You can negotiate or reject it.")

        if action == "negotiate_auto":
            memory = state.character_memory.get("auto_driver_01")
            self._require(bool(memory and memory.get("met")), "Find an auto driver before negotiating with one.")
            self._require(not memory.get("player_rejected"), "That driver has already left after you rejected the offer.")
            self._require(not memory.get("negotiated"), "You already agreed on ₹450; more bargaining may test everyone's patience.")
            memory.update({"last_offer": 450, "negotiated": True, "relationship": "impressed"})
            return Transition(definition.base_minutes or 0, "The driver sighs and agrees to ₹450. Ravi nods: “See? Polite stubbornness—a Bengaluru survival skill.”")

        if action == "reject_auto":
            memory = state.character_memory.get("auto_driver_01")
            self._require(bool(memory and memory.get("met")), "There is no auto offer to reject.")
            memory.update({"player_rejected": True, "relationship": "annoyed"})
            return Transition(definition.base_minutes or 0, "You reject the offer. The auto vanishes into traffic with impressive speed, unlike the traffic itself.")

        if action in {"take_bus", "take_cab", "use_metro", "walk"}:
            return self._travel(state, action, target)

        if action == "call_friend":
            self._require(state.battery >= 5, "Your phone needs at least 5% battery to make the call.")
            memory = state.character_memory.setdefault("friend_ananya", {})
            memory.update({"met": True, "called": True, "promise": "route_advice"})
            if "friend_ananya" not in state.characters_met:
                state.characters_met.append("friend_ananya")
            return Transition(definition.base_minutes or 0, "Ananya answers and recommends getting north via Hebbal. Ravi approves: “A useful call! Rare species.”", battery_delta=definition.battery_delta)

        if action == "charge_phone":
            self._require(state.location == Location.SILK_BOARD, "You cannot find a safe charging point here.")
            self._require(state.cash >= 20, "You need ₹20 to use the tea stall charger.")
            self._require(state.battery < 100, "Your phone is already fully charged.")
            charge = min(25, 100 - state.battery)
            return Transition(definition.base_minutes or 0, "The tea vendor guards the socket like treasure. Fifteen minutes later, your phone has more courage.", definition.cash_delta, charge)

        if action == "trade_samosa":
            self._require(state.location == Location.SILK_BOARD, "Nobody here is interested in that particular samosa.")
            self._require("cold_samosa" in state.inventory, "The cold samosa is already gone; even inventory has consequences.")
            return Transition(definition.base_minutes or 0, "The tea vendor accepts the samosa as a curiosity and gives you ₹30. Ravi refuses to ask why.", definition.cash_delta, remove_items=("cold_samosa",))

        if action == "ask_directions":
            return Transition(definition.base_minutes or 0, f"A local points toward {self._direction_hint(state)}. Ravi translates the hand gestures into an actual route.")

        if action == "interact_with_npc":
            ravi = state.character_memory["ravi"]
            ravi["warnings"] = int(ravi.get("warnings", 0)) + 1
            return Transition(definition.base_minutes or 0, "Ravi checks the clock. “Conversation is lovely, but the plane is emotionally prepared to leave without you.”")

        if action == "explore_location":
            return Transition(definition.base_minutes or 0, f"You scan {LOCATIONS[state.location].name}. {LOCATIONS[state.location].description}")

        raise RuleViolation("That action is not supported by the rules engine.")

    def _travel(self, state: GameState, action: str, target: str | None) -> Transition:
        routes = [route for route in ROUTES if route.origin == state.location and route.action == action]
        self._require(bool(routes), f"You cannot {action.replace('_', ' ')} from here.")
        destination = resolve_location_target(target)
        if target and destination is None:
            raise RuleViolation("Ravi could not match that destination to the route map.")
        if destination is not None:
            routes = [route for route in routes if route.destination == destination]
            self._require(bool(routes), f"That transport does not connect to {LOCATION_PRESENTATION[destination].label} from here.")
        elif len(routes) > 1:
            choices = " or ".join(LOCATION_PRESENTATION[route.destination].label for route in routes)
            raise RuleViolation(f"Choose a destination: {choices}.")
        route = routes[0]
        if route.requirement == "negotiated_auto":
            negotiated = state.character_memory.get("auto_driver_01", {}).get("negotiated")
            self._require(bool(negotiated), "The direct airport cab requires negotiating the auto driver's fare first.")
        self._require(state.cash >= route.cash_cost, f"You need ₹{route.cash_cost}, but only have ₹{state.cash}.")
        self._require(state.battery >= route.battery_cost, f"This trip needs {route.battery_cost}% phone battery.")
        verb = {"take_bus": "The bus", "take_cab": "The cab", "use_metro": "The metro", "walk": "The walk"}[action]
        event = self._select_event(state, route)
        extra_minutes = event.extra_minutes if event else 0
        total_minutes = route.minutes + extra_minutes
        event_text = f" {event.narrative}" if event else ""
        return Transition(
            total_minutes,
            f"{verb} gets you to {LOCATIONS[route.destination].name} in {total_minutes} game minutes.{event_text}",
            cash_delta=-route.cash_cost,
            battery_delta=-route.battery_cost,
            destination=route.destination,
        )

    @staticmethod
    def _select_event(state: GameState, route: Route):
        if not route.possible_events:
            return None
        event_key = (
            f"{state.random_seed}:{state.turn_count}:{route.origin.value}:"
            f"{route.destination.value}:{route.action}"
        )
        index = int.from_bytes(hashlib.sha256(event_key.encode()).digest()[:4], "big") % len(route.possible_events)
        return route.possible_events[index]

    def _apply(self, state: GameState, player_input: str, action: str, transition: Transition) -> ActionResult:
        before_time, before_cash, before_battery, before_location = (
            state.current_time, state.cash, state.battery, state.location
        )
        self._require(transition.minutes >= 0, "Invalid negative time transition.")
        self._require(state.cash + transition.cash_delta >= 0, "That would make your cash negative.")
        self._require(0 <= state.battery + transition.battery_delta <= 100, "That would put battery outside valid bounds.")

        state.current_time += transition.minutes
        state.cash += transition.cash_delta
        state.battery += transition.battery_delta
        for item in transition.remove_items:
            self._require(item in state.inventory, f"You no longer have {item}.")
            state.inventory.remove(item)
        for item in transition.add_items:
            if item not in state.inventory:
                state.inventory.append(item)
        if transition.destination is not None:
            state.location = transition.destination
            if transition.destination not in state.discovered_locations:
                state.discovered_locations.append(transition.destination)

        state.turn_count += 1
        state.last_action = action
        ravi_memory = state.character_memory.setdefault("ravi", {"met": True})
        observed = list(ravi_memory.get("observed_actions", []))
        observed.append(action)
        ravi_memory["observed_actions"] = observed[-5:]
        ravi_memory["last_player_decision"] = action
        state.status = self._evaluate_status(state)
        suffix = self._status_suffix(state)
        state.narrative = transition.message + suffix
        state.history.append(HistoryEntry(
            turn=state.turn_count,
            player_input=player_input,
            action=action,
            accepted=True,
            message=state.narrative,
            time_before=before_time,
            time_after=state.current_time,
            cash_delta=state.cash - before_cash,
            battery_delta=state.battery - before_battery,
        ))
        changes = StateChanges(
            time_minutes=state.current_time - before_time,
            cash=state.cash - before_cash,
            battery=state.battery - before_battery,
            added_items=list(transition.add_items),
            removed_items=list(transition.remove_items),
            location_from=before_location if state.location != before_location else None,
            location_to=state.location if state.location != before_location else None,
        )
        return ActionResult(
            accepted=True,
            message=state.narrative,
            action=action,
            changes=changes,
            state=state,
            available_actions=self.available_actions(state),
        )

    def _rejected(self, state: GameState, player_input: str, action: str | None, message: str) -> ActionResult:
        unchanged = state.model_copy(deep=True)
        ravi_memory = unchanged.character_memory.setdefault("ravi", {"met": True})
        ravi_memory["rejected_attempts"] = int(ravi_memory.get("rejected_attempts", 0)) + 1
        if action is not None:
            ravi_memory["last_rejected_action"] = action
        unchanged.history.append(HistoryEntry(
            turn=unchanged.turn_count,
            player_input=player_input,
            action=action,
            accepted=False,
            message=message,
            time_before=unchanged.current_time,
            time_after=unchanged.current_time,
        ))
        unchanged.narrative = message
        return ActionResult(
            accepted=False,
            message=message,
            action=action,
            changes=StateChanges(),
            state=unchanged,
            available_actions=self.available_actions(unchanged),
        )

    @staticmethod
    def _evaluate_status(state: GameState) -> GameStatus:
        if state.location == Location.AIRPORT:
            return GameStatus.WON if state.current_time <= state.checkin_deadline else GameStatus.LOST
        if state.current_time > state.checkin_deadline:
            return GameStatus.LOST
        return GameStatus.PLAYING

    @staticmethod
    def _status_suffix(state: GameState) -> str:
        if state.status == GameStatus.WON:
            return " You reach check-in before it closes. Ravi declares this a minor urban miracle."
        if state.status == GameStatus.LOST:
            return " The check-in deadline has passed. The airport wins this round."
        return ""

    @staticmethod
    def _direction_hint(state: GameState) -> str:
        hints = {
            Location.SILK_BOARD: "the Hebbal-bound airport bus",
            Location.HEBBAL: "the next airport bus bay",
            Location.AIRPORT_ROAD: "the terminal signs",
        }
        return hints.get(state.location, "the nearest northbound connection")

    @staticmethod
    def _require(condition: bool, message: str) -> None:
        if not condition:
            raise RuleViolation(message)

