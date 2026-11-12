import { Plane, RotateCcw, Trophy, XOctagon } from "lucide-react";
import type { GameState } from "../types/game";
import { formatGameTime } from "../utils/time";

interface EndScreenProps {
  state: GameState;
  isLoading: boolean;
  onRestart: () => void;
}

export function EndScreen({ state, isLoading, onRestart }: EndScreenProps) {
  const won = state.status === "won";
  if (state.status === "playing") return null;

  return (
    <div className="end-overlay" role="dialog" aria-modal="true" aria-labelledby="end-title">
      <section className={`end-card ${won ? "end-win" : "end-loss"}`}>
        <div className="end-icon">{won ? <Trophy size={30} /> : <XOctagon size={30} />}</div>
        <p className="eyebrow"><Plane size={14} /> Flight ESB 940</p>
        <h2 id="end-title">{won ? "Gate dreams survive." : "Check-in has closed."}</h2>
        <p>{state.narrative}</p>
        <div className="end-stats">
          <span><small>Arrival</small>{formatGameTime(state.current_time)}</span>
          <span><small>Turns</small>{state.turn_count}</span>
          <span><small>Cash left</small>₹{state.cash}</span>
        </div>
        <button onClick={onRestart} disabled={isLoading}>
          <RotateCcw size={17} /> {isLoading ? "Resetting…" : "Try another route"}
        </button>
      </section>
    </div>
  );
}
