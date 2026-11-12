import { useState, type FormEvent } from "react";
import { ArrowRight, MapPin, Plane, Timer } from "lucide-react";

interface StartScreenProps {
  isLoading: boolean;
  error: string | null;
  onStart: (name: string) => Promise<void>;
}

export function StartScreen({ isLoading, error, onStart }: StartScreenProps) {
  const [name, setName] = useState("");

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const cleanName = name.trim();
    if (cleanName) void onStart(cleanName);
  };

  return (
    <main className="start-shell">
      <div className="traffic-orbit" aria-hidden="true" />
      <section className="start-card" aria-labelledby="game-title">
        <div className="eyebrow"><MapPin size={14} /> Bengaluru · 7:00 PM</div>
        <h1 id="game-title" aria-label="Escape Silk Board">Escape<br /><span>Silk Board</span></h1>
        <p className="start-deck">
          One impossible junction. One closing check-in counter. One suspiciously cold samosa.
        </p>

        <div className="mission-strip" aria-label="Mission details">
          <div><Plane size={18} /><span><small>Flight</small>9:40 PM</span></div>
          <div><Timer size={18} /><span><small>Check-in closes</small>8:55 PM</span></div>
        </div>

        <form onSubmit={submit} className="start-form">
          <label htmlFor="player-name">What should Ravi call you?</label>
          <div className="start-input-row">
            <input
              id="player-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={40}
              placeholder="Your name"
              autoComplete="name"
              disabled={isLoading}
              autoFocus
            />
            <button type="submit" disabled={isLoading || !name.trim()}>
              {isLoading ? "Starting…" : "Enter traffic"}
              {!isLoading && <ArrowRight size={18} aria-hidden="true" />}
            </button>
          </div>
        </form>
        {error && <p className="start-error" role="alert">{error}</p>}
        <p className="start-note">Fictional routes and travel times. No real-time traffic data.</p>
      </section>
    </main>
  );
}
