import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useApp } from "@/contexts/AppContext";
import api from "@/lib/api";
import { Heart, Send } from "lucide-react";
import { toast } from "sonner";
import LangSwitch from "@/components/LangSwitch";

export default function Auth() {
  const { user, login, register, refresh, t } = useApp();
  const nav = useNavigate();
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user) {
      nav(user.onboarded ? "/" : "/onboarding", { replace: true });
    }
  }, [user, nav]);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (mode === "register") await register(email, password, name);
      else await login(email, password);
    } catch (err) {
      // Hide raw backend errors — show friendly toast based on status
      const status = err.response?.status;
      if (status === 401) toast.error(t("error"));
      else if (status === 400) toast.error(mode === "register" ? t("email") + " ✕" : t("error"));
      else if (status === 429) toast.error(t("retry"));
      else toast.error(t("error"));
    } finally {
      setLoading(false);
    }
  };

  const tryTelegram = async () => {
    const tg = window.Telegram?.WebApp;
    if (!tg?.initData) {
      toast.error(t("error"));
      return;
    }
    setLoading(true);
    try {
      const r = await api.post("/auth/telegram", { init_data: tg.initData });
      localStorage.setItem("fidem_token", r.data.token);
      await refresh();
    } catch (err) {
      toast.error(t("error"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background bg-grain flex flex-col">
      <div className="max-w-md mx-auto w-full flex-1 flex flex-col px-6 pt-12 pb-8">
        <div className="flex items-center justify-between mb-12">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-2xl bg-primary text-white grid place-items-center">
              <Heart className="w-5 h-5" fill="currentColor" />
            </div>
            <span className="font-heading text-2xl font-semibold tracking-tight">FIDEM</span>
          </div>
          <LangSwitch />
        </div>

        <h1 className="font-heading text-4xl sm:text-5xl tracking-tight font-semibold leading-[1.05]">
          {t("welcome")}.
        </h1>
        <p className="text-muted-foreground mt-3 text-base leading-relaxed">
          {t("tagline")}
        </p>

        <div className="mt-10 space-y-3">
          <button
            data-testid="btn-telegram-login"
            onClick={tryTelegram}
            disabled={loading}
            className="w-full rounded-2xl bg-secondary text-white font-medium py-3.5 px-6 flex items-center justify-center gap-2 hover:-translate-y-0.5 active:scale-[0.98] transition disabled:opacity-50"
          >
            <Send className="w-4 h-4" /> {t("continue_with_tg")}
          </button>
        </div>

        <div className="flex items-center gap-3 my-8">
          <div className="flex-1 h-px bg-border" />
          <span className="text-xs text-muted-foreground uppercase tracking-wider">or email</span>
          <div className="flex-1 h-px bg-border" />
        </div>

        <form onSubmit={submit} className="space-y-3" data-testid="auth-form">
          {mode === "register" && (
            <input
              data-testid="input-name"
              type="text"
              placeholder={t("name")}
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-2xl border border-border bg-card px-4 py-3 outline-none focus:border-primary"
            />
          )}
          <input
            data-testid="input-email"
            type="email"
            required
            placeholder={t("email")}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-2xl border border-border bg-card px-4 py-3 outline-none focus:border-primary"
          />
          <input
            data-testid="input-password"
            type="password"
            required
            placeholder={t("password")}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-2xl border border-border bg-card px-4 py-3 outline-none focus:border-primary"
          />
          <button
            data-testid="btn-submit"
            type="submit"
            disabled={loading}
            className="w-full rounded-2xl bg-primary text-white font-medium py-3.5 px-6 hover:-translate-y-0.5 active:scale-[0.98] transition disabled:opacity-50"
          >
            {mode === "login" ? t("login") : t("register")}
          </button>
        </form>
        <button
          data-testid="btn-toggle-mode"
          onClick={() => setMode((m) => (m === "login" ? "register" : "login"))}
          className="mt-4 text-sm text-muted-foreground hover:text-foreground underline-offset-4 hover:underline self-start"
        >
          {mode === "login" ? t("register") : t("login")}
        </button>

        <p className="mt-auto text-xs text-muted-foreground text-center pt-8">
          {t("safe_search")}
        </p>
      </div>
    </div>
  );
}
