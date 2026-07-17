import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import posthog from "posthog-js";
import api from "@/lib/api";
import { WS } from "@/lib/ws";
import dict, { detectLang } from "@/lib/i18n";
import { toast } from "sonner";

// Identify by id + plan only — never name/phone/photo. Matches the
// user_public() PII-safety boundary the backend already enforces.
function identifyForAnalytics(user) {
  if (!process.env.REACT_APP_POSTHOG_KEY || !user?.id) return;
  posthog.identify(user.id, { plan: user.plan || "free", is_admin: !!user.is_admin });
}

const AppCtx = createContext(null);

export function AppProvider({ children }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lang, setLang] = useState(detectLang());
  const [wsEvent, setWsEvent] = useState(null);
  const [isOnline, setIsOnline] = useState(typeof navigator !== "undefined" ? navigator.onLine : true);
  const wsRef = useRef(null);

  const t = useCallback(
    (key) => {
      const d = dict[lang];
      if (d && Object.prototype.hasOwnProperty.call(d, key)) return d[key];
      if (Object.prototype.hasOwnProperty.call(dict.uz, key)) return dict.uz[key];
      return key;
    },
    [lang]
  );

  const changeLang = (l) => {
    setLang(l);
    localStorage.setItem("fidem_lang", l);
    if (user) {
      api.patch("/profile/language", { language: l }).catch(() => {});
    }
  };

  const loadMe = useCallback(async (prefetchedUser) => {
    // login/register/telegram-auth responses already embed the full profile —
    // skip the extra GET /auth/me round-trip when we already have it.
    if (prefetchedUser) {
      setUser(prefetchedUser);
      if (prefetchedUser.language && dict[prefetchedUser.language]) {
        setLang(prefetchedUser.language);
      }
      identifyForAnalytics(prefetchedUser);
      setLoading(false);
      return prefetchedUser;
    }
    const token = localStorage.getItem("fidem_token");
    if (!token) {
      setUser(null);
      setLoading(false);
      return null;
    }
    try {
      const r = await api.get("/auth/me");
      setUser(r.data);
      if (r.data.language && dict[r.data.language]) {
        setLang(r.data.language);
      }
      identifyForAnalytics(r.data);
      return r.data;
    } catch {
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMe();
  }, [loadMe]);

  // Telegram WebApp auto-auth
  useEffect(() => {
    if (user) return;

    let cancelled = false;

    const tryTelegramAuth = async () => {
      const token = localStorage.getItem("fidem_token");
      if (token) return;

      const tg = window.Telegram?.WebApp;
      const initData = tg?.initData;

      if (!initData) {
        return false;
      }

      // Fidemadminbot opens its Mini App button straight at /admin, and
      // only ever for a Telegram id already on the admin allowlist - the
      // regular /auth/telegram endpoint validates initData against the
      // OTHER bot's token, so it would reject this session outright.
      const isAdminEntry = window.location.pathname.startsWith("/admin");
      const authPath = isAdminEntry ? "/auth/admin/telegram" : "/auth/telegram";

      try {
        const r = await api.post(authPath, {
          init_data: initData,
        });

        if (cancelled) return true;

        localStorage.setItem("fidem_token", r.data.token);
        await loadMe(r.data.user);

        if (isAdminEntry) {
          window.history.replaceState(null, "", "/admin");
        } else if (r.data.onboarded) {
          window.history.replaceState(null, "", "/");
        } else {
          window.history.replaceState(null, "", "/onboarding");
        }

        return true;
      } catch (e) {
        console.error("Telegram auto-auth failed:", e);
        return false;
      }
    };

    // Try once immediately, then retry a few times with delays
    const run = async () => {
      // Try immediately
      if (!cancelled) {
        const ok = await tryTelegramAuth();
        if (ok) return;
      }

      // Retry with exponential backoff
      for (let i = 0; i < 5; i++) {
        if (cancelled) return;
        const delay = 100 * Math.pow(2, i); // 100, 200, 400, 800, 1600ms
        await new Promise((resolve) => setTimeout(resolve, delay));
        if (cancelled) return;
        const ok = await tryTelegramAuth();
        if (ok) return;
      }
    };

    run();

    return () => {
      cancelled = true;
    };
  }, [user, loadMe]);

  // /admin can be opened from EITHER Telegram Mini App (the regular
  // Fidem_Appbot or the dedicated Fidemadminbot) - both point at this same
  // deployed app, so they share this browser's localStorage. Whichever bot
  // was opened FIRST on this device wins the stored token: someone who used
  // the regular bot before ever opening Fidemadminbot lands on /admin
  // already "logged in" as their ordinary (non-admin) dating profile, and
  // the main Telegram auto-auth above never re-runs because a token already
  // exists. If that's the case, retry specifically as the admin-bot
  // identity - it only succeeds if this Telegram id is actually on the
  // admin allowlist (ADMIN_TELEGRAM_IDS), so a non-admin still correctly
  // sees "Faqat admin uchun" afterwards.
  useEffect(() => {
    if (loading || user?.is_admin) return;
    if (!window.location.pathname.startsWith("/admin")) return;
    const initData = window.Telegram?.WebApp?.initData;
    if (!initData) return;

    let cancelled = false;
    (async () => {
      try {
        const r = await api.post("/auth/admin/telegram", { init_data: initData });
        if (cancelled) return;
        localStorage.setItem("fidem_token", r.data.token);
        await loadMe(r.data.user);
      } catch {
        // Not an admin Telegram id, or the admin bot isn't configured yet -
        // leave the existing (non-admin) session as-is.
      }
    })();
    return () => { cancelled = true; };
  }, [loading, user, loadMe]);

  const login = async (email, password) => {
    const r = await api.post("/auth/login", { email, password });
    localStorage.setItem("fidem_token", r.data.token);
    await loadMe(r.data.user);
    return r.data;
  };
  const register = async (email, password, name) => {
    const r = await api.post("/auth/register", { email, password, name });
    localStorage.setItem("fidem_token", r.data.token);
    await loadMe(r.data.user);
    return r.data;
  };
  const logout = () => {
    localStorage.removeItem("fidem_token");
    setUser(null);
    if (wsRef.current) { wsRef.current.stop(); wsRef.current = null; }
    // Clear the persisted query cache too — otherwise a different account
    // logging in on the same device would briefly paint the previous user's
    // cached candidates/chats/profile from localStorage before revalidating.
    queryClient.clear();
    try { localStorage.removeItem("fidem-query-cache"); } catch { /* ignore */ }
    if (process.env.REACT_APP_POSTHOG_KEY) posthog.reset();
    window.location.href = "/auth";
  };

  // WebSocket lifecycle — open once user is loaded, close on logout / token change
  useEffect(() => {
    const token = localStorage.getItem("fidem_token");
    if (!user || !token) {
      if (wsRef.current) { wsRef.current.stop(); wsRef.current = null; }
      return;
    }
    if (wsRef.current) return; // already open
    const ws = new WS({
      onMessage: (m) => setWsEvent({ ...m, ts: Date.now() }),
    });
    ws.start(token);
    wsRef.current = ws;
    return () => {
      ws.stop();
      wsRef.current = null;
    };
  }, [user]);

  // Money/plan-affecting notifications (P2P top-up approved, plan granted,
  // withdrawal decided, ...) can originate from an admin action the user
  // never triggered themselves — nothing else in the app calls refresh() in
  // that case, so balance/plan stayed stale until a manual page reload.
  // Silently re-fetch /auth/me whenever one of these kinds arrives over WS.
  useEffect(() => {
    if (wsEvent?.type !== "notification") return;
    const kind = wsEvent.data?.kind;
    // "gift" is included because a gifted subscription plan (Gift Shop)
    // changes the recipient's plan/boost server-side just like a direct
    // purchase would.
    if (["balance", "premium", "boost", "withdraw", "referral", "gift"].includes(kind)) {
      loadMe();
    }
  }, [wsEvent, loadMe]);

  // Online/offline detection with offline UI
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      toast.success("Internet ulanish tiklandi");
    };
    const handleOffline = () => {
      setIsOnline(false);
      toast.error("Internet ulanish yo'q. Offline rejimda ishlaysiz.");
    };
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return (
    <AppCtx.Provider
      value={{
        user, loading, lang, t, changeLang, setLang: changeLang,
        login, register, logout, refresh: loadMe,
        wsEvent, isOnline,
      }}
    >
      {children}
    </AppCtx.Provider>
  );
}

export const useApp = () => useContext(AppCtx);
