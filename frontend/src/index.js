import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PersistQueryClientProvider } from "@tanstack/react-query-persist-client";
import { createSyncStoragePersister } from "@tanstack/query-sync-storage-persister";
import "@/index.css";
import App from "@/App";

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
      staleTime: 60_000,
      gcTime: PERSIST_MAX_AGE,
      refetchOnWindowFocus: false,
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

root.render(<React.StrictMode>{Providers}</React.StrictMode>);

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
