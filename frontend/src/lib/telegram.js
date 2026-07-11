// Telegram Mini App webviews swallow plain <a target="_blank"> navigation -
// external links need the WebApp SDK's own openers or they silently do nothing.
export function openExternalLink(url) {
  if (!url) return;
  const tg = window.Telegram?.WebApp;
  const isTelegramLink = url.includes("t.me/") || url.startsWith("tg://");
  if (isTelegramLink && tg?.openTelegramLink) {
    try { tg.openTelegramLink(url); return; } catch { /* fall through */ }
  }
  if (tg?.openLink) {
    try { tg.openLink(url); return; } catch { /* fall through */ }
  }
  window.open(url, "_blank", "noopener,noreferrer");
}
