// Localized relative-time formatter for FIDEM.
// Backend returns `last_active_minutes: int` (0 = now, -1 = unknown).
// We render localised "X min ago" etc.

// Maps the app's own language toggle (uz/ru/en) to a BCP-47 locale for
// Date#toLocaleString - without this, toLocaleString() falls back to the
// browser/OS locale, which can silently mismatch the language the user
// actually picked in the app (e.g. an en-locale phone with "UZ" selected
// in-app still showed English AM/PM dates).
const DATE_LOCALE = { uz: "uz-UZ", ru: "ru-RU", en: "en-GB" };

export function localeFor(lang) {
  return DATE_LOCALE[lang] || DATE_LOCALE.uz;
}

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
