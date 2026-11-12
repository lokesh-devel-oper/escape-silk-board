import { useState, type FormEvent } from "react";
import { CornerDownLeft, Send } from "lucide-react";

interface PlayerInputProps {
  disabled: boolean;
  onSubmit: (text: string) => Promise<void>;
}

export function PlayerInput({ disabled, onSubmit }: PlayerInputProps) {
  const [text, setText] = useState("");

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const value = text.trim();
    if (!value || disabled) return;
    setText("");
    void onSubmit(value);
  };

  return (
    <form className="player-input" onSubmit={submit}>
      <label htmlFor="player-action" className="sr-only">What do you do next?</label>
      <input
        id="player-action"
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder="What do you do next?"
        maxLength={500}
        disabled={disabled}
        autoComplete="off"
      />
      <span className="enter-hint"><CornerDownLeft size={13} /> Enter</span>
      <button type="submit" disabled={disabled || !text.trim()} aria-label="Submit action">
        <Send size={18} />
      </button>
    </form>
  );
}
