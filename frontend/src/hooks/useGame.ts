import { useCallback, useEffect, useState } from "react";
import { gameApi } from "../api/gameApi";
import type { ActionResult, AvailableAction, GameState, WorldDefinition } from "../types/game";

const SESSION_KEY = "escape-silk-board-session";

function requestId(): string {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function useGame() {
  const [world, setWorld] = useState<WorldDefinition | null>(null);
  const [state, setState] = useState<GameState | null>(null);
  const [lastResult, setLastResult] = useState<ActionResult | null>(null);
  const [availableActions, setAvailableActions] = useState<AvailableAction[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isHydrating, setIsHydrating] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function hydrate() {
      try {
        setWorld(await gameApi.world());
        const saved = localStorage.getItem(SESSION_KEY);
        if (saved) {
          const restored = await gameApi.context(saved);
          setState(restored.state);
          setAvailableActions(restored.available_actions);
        }
      } catch (caught) {
        localStorage.removeItem(SESSION_KEY);
        setError(caught instanceof Error ? caught.message : "Could not load the game world.");
      } finally {
        setIsHydrating(false);
      }
    }
    void hydrate();
  }, []);

  const startGame = useCallback(async (playerName: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const next = await gameApi.newGame(playerName);
      localStorage.setItem(SESSION_KEY, next.session_id);
      const context = await gameApi.context(next.session_id);
      setState(context.state);
      setLastResult(null);
      setAvailableActions(context.available_actions);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not start the game.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const submitAction = useCallback(
    async (playerInput: string) => {
      if (!state || isLoading || state.status !== "playing") return;
      setIsLoading(true);
      setError(null);
      try {
        const result = await gameApi.action(state.session_id, playerInput, requestId());
        setState(result.state);
        setLastResult(result);
        setAvailableActions(result.available_actions);
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "That action could not be processed.");
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, state],
  );

  const restart = useCallback(async () => {
    if (!state || isLoading) return;
    setIsLoading(true);
    setError(null);
    try {
      const next = await gameApi.reset(state.session_id);
      const context = await gameApi.context(next.session_id);
      setState(context.state);
      setLastResult(null);
      setAvailableActions(context.available_actions);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not restart the game.");
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, state]);

  const clearSession = useCallback(() => {
    localStorage.removeItem(SESSION_KEY);
    setState(null);
    setLastResult(null);
    setAvailableActions([]);
    setError(null);
  }, []);

  return {
    world,
    state,
    lastResult,
    availableActions,
    isLoading,
    isHydrating,
    error,
    startGame,
    submitAction,
    restart,
    clearSession,
    clearError: () => setError(null),
  };
}
