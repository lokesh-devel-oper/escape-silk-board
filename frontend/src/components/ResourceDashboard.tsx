import { BatteryMedium, IndianRupee, MapPinned, PackageOpen, RotateCw } from "lucide-react";
import type { ActionResult, GameState } from "../types/game";
import { formatDelta } from "../utils/time";

interface ResourceDashboardProps {
  state: GameState;
  lastResult: ActionResult | null;
  locationLabel: string;
}

function Delta({ value, suffix = "" }: { value: number; suffix?: string }) {
  if (!value) return null;
  return <span className={value > 0 ? "delta delta-up" : "delta delta-down"}>{formatDelta(value, suffix)}</span>;
}

export function ResourceDashboard({ state, lastResult, locationLabel }: ResourceDashboardProps) {
  const batteryTone = state.battery <= 10 ? "resource-danger" : state.battery <= 25 ? "resource-warn" : "";

  return (
    <section className="resource-grid" aria-label="Game resources">
      <article className="resource-card">
        <IndianRupee size={18} />
        <div><span>Cash</span><strong>₹{state.cash}</strong></div>
        <Delta value={lastResult?.changes.cash ?? 0} />
      </article>
      <article className={`resource-card ${batteryTone}`}>
        <BatteryMedium size={18} />
        <div><span>Phone</span><strong>{state.battery}%</strong></div>
        <Delta value={lastResult?.changes.battery ?? 0} suffix="%" />
      </article>
      <article className="resource-card resource-location">
        <MapPinned size={18} />
        <div><span>Location</span><strong>{locationLabel}</strong></div>
      </article>
      <article className="resource-card">
        <RotateCw size={18} />
        <div><span>Turn</span><strong>{state.turn_count}</strong></div>
      </article>
      <article className="resource-card inventory-card">
        <PackageOpen size={18} />
        <div>
          <span>Inventory</span>
          <strong>{state.inventory.length ? state.inventory.map((item) => item.replaceAll("_", " ")).join(", ") : "Empty"}</strong>
        </div>
      </article>
    </section>
  );
}
