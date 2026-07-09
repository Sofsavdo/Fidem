// Theme: "system" | "light" | "dark". Persisted in localStorage and applied by
// toggling the `dark` class on <html> (Tailwind darkMode: "class"). The initial
// paint is handled by an inline script in index.html to avoid a flash.

const KEY = "fidem_theme";

export function getTheme() {
  try { return localStorage.getItem(KEY) || "system"; } catch { return "system"; }
}

export function systemIsDark() {
  const tg = window.Telegram && window.Telegram.WebApp;
  if (tg && tg.colorScheme) return tg.colorScheme === "dark";
  return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function effectiveIsDark(theme = getTheme()) {
  return theme === "dark" || (theme === "system" && systemIsDark());
}

export function applyTheme(theme = getTheme()) {
  document.documentElement.classList.toggle("dark", effectiveIsDark(theme));
}

export function setTheme(theme) {
  try { localStorage.setItem(KEY, theme); } catch { /* ignore */ }
  applyTheme(theme);
}
