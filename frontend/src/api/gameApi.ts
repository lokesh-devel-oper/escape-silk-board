import type { ActionResult, GameContext, GameState, WorldDefinition } from "../types/game";

// Local development uses Vite's same-origin proxy. Production supplies the
// public backend origin at build time through VITE_API_BASE_URL.
// When the app is hosted under a prefix (for example /gameplay/), BASE_URL
// keeps same-origin API requests inside that prefix instead of escaping to /.
const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || import.meta.env.BASE_URL || ""
).replace(/\/$/, "");

class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...init?.headers,
      },
    });
  } catch {
    throw new ApiError("The game server is unreachable. Your session is still safe.", 0);
  }

  if (!response.ok) {
    let message = "The game server could not process that request.";
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Keep the safe public message when the body is not JSON.
    }
    throw new ApiError(message, response.status);
  }
  return (await response.json()) as T;
}

export const gameApi = {
  world(): Promise<WorldDefinition> {
    return request("/api/world");
  },

  newGame(playerName: string): Promise<GameState> {
    return request("/api/game/new", {
      method: "POST",
      body: JSON.stringify({ player_name: playerName }),
    });
  },

  state(sessionId: string): Promise<GameState> {
    return request(`/api/game/state/${encodeURIComponent(sessionId)}`);
  },

  context(sessionId: string): Promise<GameContext> {
    return request(`/api/game/context/${encodeURIComponent(sessionId)}`);
  },

  action(sessionId: string, playerInput: string, requestId: string): Promise<ActionResult> {
    return request("/api/game/action", {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId,
        player_input: playerInput,
        request_id: requestId,
      }),
    });
  },

  reset(sessionId: string): Promise<GameState> {
    return request(`/api/game/reset/${encodeURIComponent(sessionId)}`, {
      method: "POST",
    });
  },
};

export { ApiError };
