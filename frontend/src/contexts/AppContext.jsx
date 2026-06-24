import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import api from "@/lib/api";
import dict, { detectLang } from "@/lib/i18n";

const AppCtx = createContext(null);

export function AppProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lang, setLang] = useState(detectLang());

  const t = useCallback(
    (key) => (dict[lang] && dict[lang][key]) || dict.uz[key] || key,
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

  // Try Telegram WebApp auto-auth on mount
  useEffect(() => {
    if (user) return;
    const tg = window.Telegram?.WebApp;
    if (!tg) return;
    try {
      tg.ready();
      tg.expand();
    } catch {}
    const initData = tg?.initData;
    const token = localStorage.getItem("fidem_token");
    if (initData && !token) {
      api
        .post("/auth/telegram", { init_data: initData })
        .then(async (r) => {
          localStorage.setItem("fidem_token", r.data.token);
          await loadMe();
        })
        .catch(() => {});
    }
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
    window.location.href = "/auth";
  };

  return (
    <AppCtx.Provider
      value={{
        user, loading, lang, t, changeLang,
        login, register, logout, refresh: loadMe,
      }}
    >
      {children}
    </AppCtx.Provider>
  );
}

export const useApp = () => useContext(AppCtx);
