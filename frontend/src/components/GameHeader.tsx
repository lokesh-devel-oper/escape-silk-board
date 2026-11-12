import { Plane, RotateCcw, Route, Timer } from "lucide-react";
import type { GameState } from "../types/game";
import { formatCountdown, formatGameTime } from "../utils/time";

interface GameHeaderProps {
  state: GameState;
  isLoading: boolean;
  onRestart: () => void;
}

export function GameHeader({ state, isLoading, onRestart }: GameHeaderProps) {
  const remaining = Math.max(0, state.checkin_deadline - state.current_time);
  const urgency = remaining <= 20 ? "critical" : remaining <= 60 ? "urgent" : "steady";

  return (
    <header className="game-header">
      <div className="brand-lockup">
        <div className="brand-mark"><Route size={21} /></div>
        <div>
          <div className="brand-title-row">
            <p>Escape Silk Board</p>
            <span className={`status-pill status-${state.status}`}>{state.status}</span>
          </div>
          <span>Flight ESB 940 · BLR</span>
        </div>
      </div>

      <div className="flight-clock" aria-label="Flight timing">
        <div>
          <span><Plane size={14} /> Current time</span>
          <strong>{formatGameTime(state.current_time)}</strong>
        </div>
        <div className={`countdown countdown-${urgency}`}>
          <span><Timer size={14} /> Check-in countdown</span>
          <strong>{formatCountdown(state.current_time, state.checkin_deadline)}</strong>
        </div>
      </div>

      <button className="icon-button restart-button" onClick={onRestart} disabled={isLoading}>
        <RotateCcw size={16} aria-hidden="true" />
        <span>Restart</span>
      </button>
    </header>
  );
}
