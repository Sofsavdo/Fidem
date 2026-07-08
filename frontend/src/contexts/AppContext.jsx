import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from "react";
import api from "@/lib/api";
import { WS } from "@/lib/ws";
import dict, { detectLang } from "@/lib/i18n";
import { toast } from "sonner";

const AppCtx = createContext(null);

export function AppProvider({ children }) {
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

  const loadMe = useCallback(async () => {
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
        console.log("No Telegram initData available");
        return false;
      }

      try {
        console.log("Attempting Telegram auth...");
        tg.ready?.();
        tg.expand?.();

        const r = await api.post("/auth/telegram", {
          init_data: initData,
        });

        if (cancelled) return true;

        localStorage.setItem("fidem_token", r.data.token);
        await loadMe();

        if (r.data.onboarded) {
          window.history.replaceState(null, "", "/");
        } else {
          window.history.replaceState(null, "", "/onboarding");
        }

        console.log("Telegram auth successful");
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
      
      console.log("Telegram auth failed after retries");
    };

    run();

    return () => {
      cancelled = true;
    };
  }, [user, loadMe]);
  const login = async (email, password) => {
    const r = await api.post("/auth/login", { email, password });
    localStorage.setItem("fidem_token", r.data.token);
    await loadMe();
    return r.data;
  };
  const register = async (email, password, name) => {
    const r = await api.post("/auth/register", { email, password, name });
    localStorage.setItem("fidem_token", r.data.token);
    await loadMe();
    return r.data;
  };
  const logout = () => {
    localStorage.removeItem("fidem_token");
    setUser(null);
    if (wsRef.current) { wsRef.current.stop(); wsRef.current = null; }
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
