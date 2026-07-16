import { useLayoutEffect } from "react";
import { useLocation } from "react-router-dom";
import posthog from "posthog-js";

// Stop the browser restoring window scroll on reload/back — the app resets
// scroll itself on every navigation.
try { window.history.scrollRestoration = "manual"; } catch { /* older webviews */ }

/**
 * Scroll to top on every route change.
 * Mount once inside <BrowserRouter>.
 *
 * The reset is deliberately aggressive: the app-shell reuses one scroll
 * container (#app-scroll) across routes, so its scrollTop survives
 * navigation, and on slow devices late layout shifts (fonts, images, data
 * arriving) could leave the new page opened mid-way. We reset before paint,
 * on the next frame, and twice more while late content lands, hitting both
 * the shell scroller and the window (for pages rendered outside the shell).
 * Keyed on search too, so tab switches (?tab=...) also start at the top.
 */
export default function ScrollToTop() {
  const { pathname, search } = useLocation();
  useLayoutEffect(() => {
    const reset = () => {
      const el = document.getElementById("app-scroll");
      if (el) el.scrollTop = 0;
      window.scrollTo(0, 0);
    };
    reset();
    // Chat manages its own scroll (auto-scrolls to the latest message), and
    // ?hl= deep links scroll TO a highlighted plan — don't fight either.
    const skipLate = pathname.startsWith("/chat/") || search.includes("hl=");
    const raf = skipLate ? 0 : requestAnimationFrame(reset);
    const t1 = skipLate ? 0 : setTimeout(reset, 150);
    const t2 = skipLate ? 0 : setTimeout(reset, 450);
    if (process.env.REACT_APP_POSTHOG_KEY) {
      posthog.capture("$pageview", { $current_url: pathname });
    }
    return () => { cancelAnimationFrame(raf); clearTimeout(t1); clearTimeout(t2); };
  }, [pathname, search]);
  return null;
}
