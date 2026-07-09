import React from "react";
import ReactDOM from "react-dom/client";
import * as Sentry from "@sentry/react";
import posthog from "posthog-js";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PersistQueryClientProvider } from "@tanstack/react-query-persist-client";
import { createSyncStoragePersister } from "@tanstack/query-sync-storage-persister";
import "@/index.css";
import App from "@/App";

// Catches render-time crashes (e.g. a stray reference to removed state after
// a refactor) that would otherwise leave the Telegram Mini App on a blank
// white screen with zero visibility into what broke.
if (process.env.REACT_APP_SENTRY_DSN) {
  Sentry.init({
    dsn: process.env.REACT_APP_SENTRY_DSN,
    environment: process.env.REACT_APP_SENTRY_ENVIRONMENT || "production",
    tracesSampleRate: 0.1,
    sendDefaultPii: false,
  });
}

// Product analytics — which pages/funnels actually get used, where users
// drop off before paying. Autocapture only (clicks/pageviews); user identity
// is attached separately in AppContext once we know the logged-in id, never
// with name/phone/photo attached.
if (process.env.REACT_APP_POSTHOG_KEY) {
  posthog.init(process.env.REACT_APP_POSTHOG_KEY, {
    api_host: process.env.REACT_APP_POSTHOG_HOST || "https://us.i.posthog.com",
    person_profiles: "identified_only",
    capture_pageview: false, // App.js has client-side routing — captured manually on route change instead
  });
}

// Hand off from Telegram's native loading splash to our own UI as early as
// possible — this must run before React mounts, not inside a component
// effect, or the splash lingers through the whole auth round-trip.
try {
  const tg = window.Telegram?.WebApp;
  if (tg) {
    tg.ready();
    tg.expand();
    if (tg.setHeaderColor) tg.setHeaderColor("#ffffff");
    if (tg.setBackgroundColor) tg.setBackgroundColor("#ffffff");
    if (tg.enableClosingConfirmation) tg.enableClosingConfirmation();
  }
} catch (e) {
  console.error("Telegram WebApp init error:", e);
}

// 24h: how long persisted cache entries stay usable across app restarts.
// Older than this and we'd rather show a loading state than stale/wrong data
// (e.g. a candidate who deactivated weeks ago).
const PERSIST_MAX_AGE = 24 * 60 * 60 * 1000;

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Longer stale window so re-opening a page within a session paints
      // instantly from cache instead of re-flashing a skeleton; mutations
      // invalidate the affected keys explicitly, so balance/payment-sensitive
      // data still updates immediately after an action.
      staleTime: 3 * 60_000,
      gcTime: PERSIST_MAX_AGE,
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

// Persists the query cache to localStorage so re-opening the app (Telegram
// Mini App relaunch, slow/flaky connection, or briefly offline) paints the
// last-seen candidates/chats/profile instantly from disk instead of a blank
// loading state, then silently revalidates in the background per each
// query's normal staleTime. This is the "feels instant like a native app"
// behavior — no bespoke offline system, just React Query's own persistence.
let persister;
try {
  persister = createSyncStoragePersister({ storage: window.localStorage, key: "fidem-query-cache" });
} catch (e) {
  // localStorage unavailable (private browsing, storage disabled) - app
  // still works, it just always fetches fresh instead of painting from cache.
  persister = null;
}

const root = ReactDOM.createRoot(document.getElementById("root"));
const Providers = persister
  ? (
    <PersistQueryClientProvider
      client={queryClient}
      persistOptions={{
        persister,
        maxAge: PERSIST_MAX_AGE,
        dehydrateOptions: {
          // Never persist admin-only data to a device's local storage.
          shouldDehydrateQuery: (query) => query.queryKey[0] !== "admin",
        },
      }}
    >
      <App />
    </PersistQueryClientProvider>
  )
  : (
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  );

function CrashFallback() {
  return (
    <div style={{
      minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center",
      justifyContent: "center", gap: 16, padding: 24, textAlign: "center", fontFamily: "Manrope, sans-serif",
    }}>
      <p style={{ fontSize: 15, color: "#6B6058" }}>Nimadir noto'g'ri ketdi. Iltimos, sahifani qayta yuklang.</p>
      <button
        onClick={() => window.location.reload()}
        style={{
          borderRadius: 16, padding: "12px 28px", background: "#9E4735", color: "white",
          fontWeight: 600, border: 0, cursor: "pointer",
        }}
      >
        Qayta yuklash
      </button>
    </div>
  );
}

root.render(
  <React.StrictMode>
    <Sentry.ErrorBoundary fallback={<CrashFallback />}>
      {Providers}
    </Sentry.ErrorBoundary>
  </React.StrictMode>
);

if ("serviceWorker" in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then((registration) => {
        console.log('Service Worker registered: ', registration);
      })
      .catch((registrationError) => {
        console.log('Service Worker registration failed: ', registrationError);
      });
  });
}
