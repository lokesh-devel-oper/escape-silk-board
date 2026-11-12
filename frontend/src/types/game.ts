export type GameStatus = "playing" | "won" | "lost";

export type LocationId = string;

export interface HistoryEntry {
  turn: number;
  player_input: string;
  action: string | null;
  accepted: boolean;
  message: string;
  time_before: number;
  time_after: number;
  cash_delta: number;
  battery_delta: number;
}

export interface GameState {
  session_id: string;
  player_name: string;
  current_time: number;
  checkin_deadline: number;
  flight_time: number;
  location: LocationId;
  cash: number;
  battery: number;
  inventory: string[];
  turn_count: number;
  status: GameStatus;
  history: HistoryEntry[];
  characters_met: string[];
  character_memory: Record<string, Record<string, unknown>>;
  discovered_locations: LocationId[];
  narrative: string;
  last_action: string | null;
  random_seed: number;
}

export interface StateChanges {
  time_minutes: number;
  cash: number;
  battery: number;
  added_items: string[];
  removed_items: string[];
  location_from: LocationId | null;
  location_to: LocationId | null;
}

export interface AIMetadata {
  source: "gemini" | "deterministic";
  attempts: number;
  fallback_reason: string | null;
}

export interface AvailableAction {
  action_id: string;
  label: string;
  command: string;
  description: string;
  category: "travel" | "social" | "resource" | "exploration";
  priority: number;
  target: LocationId | null;
  enabled: boolean;
  disabled_reason: string | null;
  minutes: number | null;
  cash_cost: number;
  battery_cost: number;
}

export interface WorldLocation {
  id: LocationId;
  label: string;
  description: string;
  lane: "main" | "alternate";
  order: number;
  progress: number;
  is_destination: boolean;
}

export interface WorldRoute {
  origin: LocationId;
  destination: LocationId;
  action_id: string;
  minutes: number;
  cash_cost: number;
  battery_cost: number;
  requirement: string | null;
}

export interface WorldAction {
  id: string;
  label: string;
  description: string;
  category: AvailableAction["category"];
  priority: number;
}

export interface WorldDefinition {
  version: string;
  locations: WorldLocation[];
  routes: WorldRoute[];
  actions: WorldAction[];
}

export interface GameContext {
  state: GameState;
  available_actions: AvailableAction[];
}

export interface ActionResult {
  accepted: boolean;
  message: string;
  action: string | null;
  changes: StateChanges;
  state: GameState;
  available_actions: AvailableAction[];
  duplicate: boolean;
  interpretation: AIMetadata;
  narration: AIMetadata;
}
