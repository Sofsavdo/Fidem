import { useLayoutEffect } from "react";
import { useLocation } from "react-router-dom";
import posthog from "posthog-js";

/**
 * Scroll to top on every route change.
 * Mount once inside <BrowserRouter>.
 *
 * The reset is deliberately aggressive: the app-shell reuses one scroll
 * container (#app-scroll) across routes, so its scrollTop survives
 * navigation, and on slow devices late layout shifts (fonts, images, data
 * arriving) could leave the new page opened mid-way. We reset before paint,
 * on the next frame, and once more shortly after, hitting both the shell
 * scroller and the window (for pages rendered outside the shell).
 */
export default function ScrollToTop() {
  const { pathname } = useLocation();
  useLayoutEffect(() => {
    const reset = () => {
      const el = document.getElementById("app-scroll");
      if (el) el.scrollTop = 0;
      window.scrollTo(0, 0);
    };
    reset();
    // Chat manages its own scroll (auto-scrolls to the latest message), so
    // don't fire the delayed resets there - they could yank it back up.
    const isChat = pathname.startsWith("/chat/");
    const raf = isChat ? 0 : requestAnimationFrame(reset);
    const timer = isChat ? 0 : setTimeout(reset, 120);
    if (process.env.REACT_APP_POSTHOG_KEY) {
      posthog.capture("$pageview", { $current_url: pathname });
    }
    return () => { cancelAnimationFrame(raf); clearTimeout(timer); };
  }, [pathname]);
  return null;
}
