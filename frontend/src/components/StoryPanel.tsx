import { useEffect, useRef } from "react";
import { Bot, UserRound, XCircle } from "lucide-react";
import type { GameState } from "../types/game";
import { formatGameTime } from "../utils/time";

interface StoryPanelProps {
  state: GameState;
  isLoading: boolean;
}

export function StoryPanel({ state, isLoading }: StoryPanelProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [state.history.length, isLoading]);

  return (
    <section className="story-panel" aria-label="Adventure story">
      <div className="panel-heading">
        <div><span className="live-dot" /> Live dispatch</div>
        <span>{state.history.length} exchanges</span>
      </div>
      <div className="story-scroll" aria-live="polite">
        <article className="dialogue dialogue-ravi">
          <div className="avatar avatar-ravi"><Bot size={17} /></div>
          <div className="dialogue-body">
            <div className="speaker"><strong>Ravi</strong><span>{formatGameTime(1140)}</span></div>
            <p>{state.history.length ? "I remember how this traffic tragedy began." : state.narrative}</p>
          </div>
        </article>

        {state.history.map((entry, index) => (
          <div className="story-exchange" key={`${index}-${entry.player_input}-${entry.time_after}`}>
            <article className="dialogue dialogue-player">
              <div className="avatar"><UserRound size={16} /></div>
              <div className="dialogue-body">
                <div className="speaker"><strong>{state.player_name}</strong><span>{formatGameTime(entry.time_before)}</span></div>
                <p>{entry.player_input}</p>
              </div>
            </article>
            <article className={`dialogue dialogue-ravi ${!entry.accepted ? "dialogue-rejected" : ""}`}>
              <div className="avatar avatar-ravi">
                {entry.accepted ? <Bot size={17} /> : <XCircle size={17} />}
              </div>
              <div className="dialogue-body">
                <div className="speaker">
                  <strong>{entry.accepted ? "Ravi" : "Action rejected"}</strong>
                  <span>{formatGameTime(entry.time_after)}</span>
                </div>
                <p>{entry.message}</p>
                {entry.accepted && (entry.cash_delta !== 0 || entry.battery_delta !== 0 || entry.time_after !== entry.time_before) && (
                  <div className="consequence-row">
                    {entry.time_after !== entry.time_before && <span>+{entry.time_after - entry.time_before} min</span>}
                    {entry.cash_delta !== 0 && <span>{entry.cash_delta > 0 ? "+" : ""}₹{entry.cash_delta}</span>}
                    {entry.battery_delta !== 0 && <span>{entry.battery_delta > 0 ? "+" : ""}{entry.battery_delta}% battery</span>}
                  </div>
                )}
              </div>
            </article>
          </div>
        ))}

        {isLoading && (
          <article className="dialogue dialogue-ravi loading-dialogue" role="status">
            <div className="avatar avatar-ravi"><Bot size={17} /></div>
            <div className="typing-dots" aria-label="Ravi is thinking"><i /><i /><i /></div>
          </article>
        )}
        <div ref={endRef} />
      </div>
    </section>
  );
}
