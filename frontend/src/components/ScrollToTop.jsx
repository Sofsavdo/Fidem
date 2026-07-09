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
    // The app-shell's content area (#app-scroll) is the actual scroll
    // container now, not the window — scroll it (with a window fallback
    // for pages rendered outside the shell, e.g. before auth).
    const el = document.getElementById("app-scroll");
    try {
      if (el) el.scrollTo({ top: 0, left: 0, behavior: "instant" });
      else window.scrollTo({ top: 0, left: 0, behavior: "instant" });
    } catch {
      if (el) el.scrollTop = 0;
      else window.scrollTo(0, 0);
    }
    if (process.env.REACT_APP_POSTHOG_KEY) {
      posthog.capture("$pageview", { $current_url: pathname });
    }
  }, [pathname]);
  return null;
}
