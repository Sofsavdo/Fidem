// Guest mode: someone who came in through Telegram but hasn't finished the
// profile can look around; every action opens the "finish registration" sheet.
export const NEED_REGISTRATION_EVENT = "fidem:need-registration";

export const isGuest = (user) => !!user && !user.onboarded && !user.is_admin;

export function askToRegister(reason = "") {
  window.dispatchEvent(new CustomEvent(NEED_REGISTRATION_EVENT, { detail: { reason } }));
}

// Where to come back after the onboarding (Onboarding.jsx reads it).
export function rememberReturnPath(path) {
  try { sessionStorage.setItem("fidem_after_onboarding", path || "/"); } catch { /* private mode */ }
}
