import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import posthog from "posthog-js";

/**
 * Scroll window to top on every route change.
 * Mount once inside <BrowserRouter>.
 */
export default function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    // Use 'instant' so the user lands directly at the top of a new page (no jank).
    try {
      window.scrollTo({ top: 0, left: 0, behavior: "instant" });
    } catch {
      window.scrollTo(0, 0);
    }
    if (process.env.REACT_APP_POSTHOG_KEY) {
      posthog.capture("$pageview", { $current_url: pathname });
    }
  }, [pathname]);
  return null;
}
