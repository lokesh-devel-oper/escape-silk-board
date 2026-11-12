import { AlertTriangle, LogOut, X } from "lucide-react";
import { ActionSuggestions } from "./components/ActionSuggestions";
import { EndScreen } from "./components/EndScreen";
import { GameHeader } from "./components/GameHeader";
import { PlayerInput } from "./components/PlayerInput";
import { ResourceDashboard } from "./components/ResourceDashboard";
import { RouteMap } from "./components/RouteMap";
import { StartScreen } from "./components/StartScreen";
import { StoryPanel } from "./components/StoryPanel";
import { useGame } from "./hooks/useGame";

export default function App() {
  const game = useGame();

  if (game.isHydrating) {
    return <main className="boot-screen"><span className="boot-spinner" /><p>Finding your place in traffic…</p></main>;
  }

  if (!game.world) {
    return (
      <main className="boot-screen">
        <AlertTriangle size={24} />
        <p>{game.error ?? "The route network could not be loaded."}</p>
        <button onClick={() => globalThis.location.reload()}>Retry</button>
      </main>
    );
  }

  if (!game.state) {
    return <StartScreen isLoading={game.isLoading} error={game.error} onStart={game.startGame} />;
  }

  const submitSuggestion = (label: string) => void game.submitAction(label);
  const currentLocation = game.world.locations.find((location) => location.id === game.state?.location);
  const lastAction = game.world.actions.find((action) => action.id === game.state?.last_action);

  return (
    <main className="game-shell">
      <div className="road-lines" aria-hidden="true" />
      <GameHeader state={game.state} isLoading={game.isLoading} onRestart={game.restart} />

      {game.error && (
        <div className="error-banner" role="alert">
          <AlertTriangle size={17} />
          <span>{game.error}</span>
          <button onClick={game.clearError} aria-label="Dismiss error"><X size={16} /></button>
        </div>
      )}

      <ResourceDashboard
        state={game.state}
        lastResult={game.lastResult}
        locationLabel={currentLocation?.label ?? game.state.location.replaceAll("_", " ")}
      />

      <div className="game-layout">
        <div className="narrative-column">
          <StoryPanel state={game.state} isLoading={game.isLoading} />
          {game.state.status === "playing" && (
            <div className="command-deck">
              <ActionSuggestions
                actions={game.availableActions}
                disabled={game.isLoading}
                onAction={submitSuggestion}
              />
              <PlayerInput disabled={game.isLoading} onSubmit={game.submitAction} />
            </div>
          )}
        </div>

        <aside className="intel-column">
          <RouteMap state={game.state} world={game.world} />
          <section className="ravi-card">
            <div className="ravi-monogram">R</div>
            <div>
              <span>Local intelligence</span>
              <strong>Ravi is riding shotgun</strong>
              <p>{game.state.last_action ? `He remembers: ${lastAction?.label ?? game.state.last_action}.` : "Street-smart. Sarcastic. Alarmingly calm."}</p>
            </div>
          </section>
          <button className="leave-button" onClick={game.clearSession}>
            <LogOut size={15} /> Leave this session
          </button>
        </aside>
      </div>

      <EndScreen state={game.state} isLoading={game.isLoading} onRestart={game.restart} />
    </main>
  );
}
