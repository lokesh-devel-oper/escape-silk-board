import { Sparkles } from "lucide-react";
import type { AvailableAction } from "../types/game";

interface ActionSuggestionsProps {
  actions: AvailableAction[];
  disabled: boolean;
  onAction: (text: string) => void;
}

export function ActionSuggestions({ actions, disabled, onAction }: ActionSuggestionsProps) {
  const visible = actions.slice(0, 6);
  if (!visible.length) return null;

  return (
    <div className="suggestions" aria-label="Suggested actions">
      <span><Sparkles size={13} /> Try</span>
      <div>
        {visible.map((action) => {
          const details = [
            action.minutes !== null ? `${action.minutes} min` : null,
            action.cash_cost ? `₹${action.cash_cost}` : null,
            action.battery_cost ? `${action.battery_cost}% battery` : null,
          ].filter(Boolean).join(" · ");
          return (
            <button
              key={`${action.action_id}:${action.target ?? "none"}`}
              aria-label={action.label}
              disabled={disabled || !action.enabled}
              onClick={() => onAction(action.command)}
              title={action.disabled_reason ?? action.description}
            >
              <strong>{action.label}</strong>
              {(action.disabled_reason || details) && (
                <small>{action.disabled_reason ?? details}</small>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
