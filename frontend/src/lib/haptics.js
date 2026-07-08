// Native-feeling tactile feedback via Telegram's WebApp API. No-ops safely
// outside Telegram (web browser) or on devices without haptics. Keeping the
// calls tiny and centralised means any tap target can feel instant/native
// with one import — this is the cheapest "premium app" signal available.
function hf() {
  try {
    return window.Telegram?.WebApp?.HapticFeedback || null;
  } catch {
    return null;
  }
}

// Light tap — navigation, toggles, opening things.
export function tapLight() {
  try { hf()?.impactOccurred?.("light"); } catch { /* ignore */ }
}

// Medium tap — committing an action (send, save, buy).
export function tapMedium() {
  try { hf()?.impactOccurred?.("medium"); } catch { /* ignore */ }
}

// Success / warning / error — outcome of an action.
export function notify(type = "success") {
  try { hf()?.notificationOccurred?.(type); } catch { /* ignore */ }
}

// Selection moved (tab switch, pill change).
export function selection() {
  try { hf()?.selectionChanged?.(); } catch { /* ignore */ }
}
