// Localized relative-time formatter for FIDEM.
// Backend returns `last_active_minutes: int` (0 = now, -1 = unknown).
// We render localised "X min ago" etc.

export function formatLastActive(minutes, t, online) {
  if (online) return t("online") || "Online";
  if (minutes === undefined || minutes === null || minutes < 0) return "—";
  if (minutes < 5) return t("online") || "Online";
  if (minutes < 60) return `${minutes} ${t("min_word")}`;
  const h = Math.floor(minutes / 60);
  if (h < 24) return `${h} ${t("hour_word")}`;
  const d = Math.floor(h / 24);
  return `${d} ${t("day_word")}`;
}
