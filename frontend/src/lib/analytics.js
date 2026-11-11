import posthog from "posthog-js";

// Product funnel events: signup -> onboarded -> photo -> first like -> first
// message -> paywall -> purchase. One tiny wrapper so a missing/blocked analytics
// key can never break the app.
export function track(event, props) {
  try {
    if (process.env.REACT_APP_POSTHOG_KEY) posthog.capture(event, props);
  } catch { /* analytics must never throw into the UI */ }
}
