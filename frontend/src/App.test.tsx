import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import type { ActionResult, AvailableAction, GameState, WorldDefinition } from "./types/game";

function option(
  action_id: string,
  label: string,
  target: string | null = null,
): AvailableAction {
  return {
    action_id,
    label,
    command: label,
    description: label,
    category: target ? "travel" : "exploration",
    priority: 10,
    target,
    enabled: true,
    disabled_reason: null,
    minutes: null,
    cash_cost: 0,
    battery_cost: 0,
  };
}

const world: WorldDefinition = {
  version: "1.0",
  locations: [
    { id: "silk_board", label: "Silk Board", description: "Start", lane: "main", order: 0, progress: 4, is_destination: false },
    { id: "hebbal", label: "Hebbal", description: "North", lane: "main", order: 1, progress: 66, is_destination: false },
    { id: "kempegowda_international_airport", label: "KIA Terminal", description: "Finish", lane: "main", order: 2, progress: 100, is_destination: true },
  ],
  routes: [
    { origin: "silk_board", destination: "hebbal", action_id: "take_bus", minutes: 62, cash_cost: 50, battery_cost: 0, requirement: null },
  ],
  actions: [
    { id: "take_bus", label: "Take the bus", description: "Travel by bus", category: "travel", priority: 10 },
  ],
};

const initialActions = [option("take_bus", "Take the bus to Hebbal", "hebbal")];

const initialState: GameState = {
  session_id: "session-1",
  player_name: "Maya",
  current_time: 1140,
  checkin_deadline: 1255,
  flight_time: 1300,
  location: "silk_board",
  cash: 500,
  battery: 32,
  inventory: ["cold_samosa"],
  turn_count: 0,
  status: "playing",
  history: [],
  characters_met: ["ravi"],
  character_memory: { ravi: { met: true } },
  discovered_locations: ["silk_board"],
  narrative: "Ravi says the traffic has achieved sentience.",
  last_action: null,
  random_seed: 7,
};

const busState: GameState = {
  ...initialState,
  current_time: 1202,
  location: "hebbal",
  cash: 450,
  turn_count: 1,
  last_action: "take_bus",
  discovered_locations: ["silk_board", "hebbal"],
  narrative: "The bus gets you to Hebbal. Ravi approves, reluctantly.",
  history: [
    {
      turn: 1,
      player_input: "Take the bus",
      action: "take_bus",
      accepted: true,
      message: "The bus gets you to Hebbal. Ravi approves, reluctantly.",
      time_before: 1140,
      time_after: 1202,
      cash_delta: -50,
      battery_delta: 0,
    },
  ],
};

const busResult: ActionResult = {
  accepted: true,
  message: busState.narrative,
  action: "take_bus",
  changes: {
    time_minutes: 62,
    cash: -50,
    battery: 0,
    added_items: [],
    removed_items: [],
    location_from: "silk_board",
    location_to: "hebbal",
  },
  state: busState,
  available_actions: [option("take_bus", "Take the bus to KIA Terminal", "kempegowda_international_airport")],
  duplicate: false,
  interpretation: { source: "deterministic", attempts: 0, fallback_reason: "not_configured" },
  narration: { source: "deterministic", attempts: 0, fallback_reason: "not_configured" },
};

function jsonResponse(body: unknown, status = 200): Promise<Response> {
  return Promise.resolve(new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  }));
}

async function startGame(user: ReturnType<typeof userEvent.setup>) {
  await screen.findByRole("heading", { level: 1 });
  await user.type(screen.getByLabelText(/what should ravi call you/i), "Maya");
  await user.click(screen.getByRole("button", { name: /enter traffic/i }));
  await screen.findByText("₹500");
}

describe("Escape Silk Board app", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    vi.stubGlobal("crypto", { randomUUID: () => "request-123" });
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("starts a game and renders the full dashboard", async () => {
    vi.mocked(fetch)
      .mockImplementationOnce(() => jsonResponse(world))
      .mockImplementationOnce(() => jsonResponse(initialState, 201))
      .mockImplementationOnce(() => jsonResponse({ state: initialState, available_actions: initialActions }));
    const user = userEvent.setup();
    render(<App />);

    await startGame(user);

    expect(screen.getAllByText("Silk Board", { selector: "strong" }).length).toBeGreaterThan(0);
    expect(screen.getByText("32%")).toBeInTheDocument();
    expect(screen.getByText(/traffic has achieved sentience/i)).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /adventure story/i })).toBeInTheDocument();
    expect(localStorage.getItem("escape-silk-board-session")).toBe("session-1");
  });

  it("submits natural language and immediately renders authoritative changes", async () => {
    vi.mocked(fetch)
      .mockImplementationOnce(() => jsonResponse(world))
      .mockImplementationOnce(() => jsonResponse(initialState, 201))
      .mockImplementationOnce(() => jsonResponse({ state: initialState, available_actions: initialActions }))
      .mockImplementationOnce(() => jsonResponse(busResult));
    const user = userEvent.setup();
    render(<App />);
    await startGame(user);

    await user.type(screen.getByLabelText(/what do you do next/i), "Take the bus");
    await user.click(screen.getByRole("button", { name: /submit action/i }));

    expect(await screen.findByText("Hebbal", { selector: ".resource-card strong" })).toBeInTheDocument();
    expect(screen.getByText("₹450")).toBeInTheDocument();
    expect(screen.getByText(/ravi approves, reluctantly/i)).toBeInTheDocument();
    expect(screen.getByText("+62 min")).toBeInTheDocument();

    const actionCall = vi.mocked(fetch).mock.calls[3];
    const body = JSON.parse(String(actionCall[1]?.body));
    expect(body).toMatchObject({
      session_id: "session-1",
      player_input: "Take the bus",
      request_id: "request-123",
    });
  });

  it("preserves the session and displays a recoverable API error", async () => {
    vi.mocked(fetch)
      .mockImplementationOnce(() => jsonResponse(world))
      .mockImplementationOnce(() => jsonResponse(initialState, 201))
      .mockImplementationOnce(() => jsonResponse({ state: initialState, available_actions: initialActions }))
      .mockImplementationOnce(() => jsonResponse({ detail: "Temporary traffic-control failure." }, 503));
    const user = userEvent.setup();
    render(<App />);
    await startGame(user);

    await user.type(screen.getByLabelText(/what do you do next/i), "Look around");
    await user.click(screen.getByRole("button", { name: /submit action/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Temporary traffic-control failure");
    expect(screen.getByText("₹500")).toBeInTheDocument();
    expect(localStorage.getItem("escape-silk-board-session")).toBe("session-1");
  });

  it("restores a saved session and shows the terminal victory screen", async () => {
    const wonState: GameState = {
      ...busState,
      location: "kempegowda_international_airport",
      status: "won",
      current_time: 1255,
      narrative: "You reach check-in at the last possible moment.",
    };
    localStorage.setItem("escape-silk-board-session", "session-1");
    vi.mocked(fetch)
      .mockImplementationOnce(() => jsonResponse(world))
      .mockImplementationOnce(() => jsonResponse({ state: wonState, available_actions: [] }));

    render(<App />);

    expect(await screen.findByRole("heading", { name: /gate dreams survive/i })).toBeInTheDocument();
    expect(screen.getAllByText("8:55 PM").length).toBeGreaterThan(0);
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(
      "/api/game/context/session-1",
      expect.any(Object),
    ));
  });
});
