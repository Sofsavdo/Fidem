import { useEffect, useState } from "react";
import posthog from "posthog-js";

// A/B experiments via PostHog feature flags.
//
// Usage:
//   const variant = useExperiment("candidates-promo-copy"); // "control" | "urgent" | ...
//
// Contract:
// - Returns the flag's string variant once PostHog delivers flags, and
//   `fallback` ("control") before that / when PostHog isn't configured /
//   when the flag doesn't exist yet. Callers must treat the fallback as the
//   production default, so shipping this code BEFORE creating the flag in
//   the PostHog dashboard is always safe.
// - Reading the flag goes through posthog.getFeatureFlag(), which also
//   reports the $feature_flag_called exposure event PostHog experiments use
//   for their results — no extra bookkeeping needed here.

const POSTHOG_ENABLED = !!process.env.REACT_APP_POSTHOG_KEY;

export function useExperiment(flagKey, fallback = "control") {
  const [variant, setVariant] = useState(() => {
    if (!POSTHOG_ENABLED) return fallback;
    const v = posthog.getFeatureFlag(flagKey);
    return typeof v === "string" ? v : fallback;
  });

  useEffect(() => {
    if (!POSTHOG_ENABLED) return undefined;
    // Flags usually arrive shortly after init; onFeatureFlags fires both on
    // load and on any later reload (e.g. after identify()).
    const unsubscribe = posthog.onFeatureFlags(() => {
      const v = posthog.getFeatureFlag(flagKey);
      setVariant(typeof v === "string" ? v : fallback);
    });
    // Older posthog-js versions return undefined instead of an unsubscriber.
    return () => { if (typeof unsubscribe === "function") unsubscribe(); };
  }, [flagKey, fallback]);

  return variant;
}
