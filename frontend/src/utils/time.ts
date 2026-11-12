export function formatGameTime(minutes: number): string {
  const hours24 = Math.floor(minutes / 60) % 24;
  const mins = minutes % 60;
  const suffix = hours24 >= 12 ? "PM" : "AM";
  const hours12 = hours24 % 12 || 12;
  return `${hours12}:${mins.toString().padStart(2, "0")} ${suffix}`;
}

export function formatCountdown(current: number, deadline: number): string {
  const remaining = Math.max(0, deadline - current);
  const hours = Math.floor(remaining / 60);
  const minutes = remaining % 60;
  return hours > 0 ? `${hours}h ${minutes.toString().padStart(2, "0")}m` : `${minutes}m`;
}

export function formatDelta(value: number, suffix = ""): string {
  return `${value > 0 ? "+" : ""}${value}${suffix}`;
}
