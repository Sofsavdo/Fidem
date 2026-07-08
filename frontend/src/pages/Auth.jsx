import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useApp } from "@/contexts/AppContext";
import api from "@/lib/api";
import { Heart, Send, Mail, Lock, User as UserIcon, ArrowRight, ShieldCheck, Sparkles } from "lucide-react";
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
  const [showPwd, setShowPwd] = useState(false);

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
      await refresh(r.data.user);
    } catch (err) {
      toast.error(t("error"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen bg-background bg-grain overflow-hidden">
      {/* Decorative gradient orbs */}
      <div className="orb orb-1" />
      <div className="orb orb-2" />
      <div className="orb orb-3" />

      <div className="relative z-10 max-w-md mx-auto w-full min-h-screen flex flex-col px-5 pt-8 pb-10 sm:px-6 sm:pt-12">
        {/* Top bar */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-[hsl(11_55%_46%)] to-[hsl(11_50%_36%)] text-white grid place-items-center shadow-lg shadow-primary/30">
              <Heart className="w-5 h-5" fill="currentColor" />
            </div>
            <span className="font-heading text-2xl font-semibold tracking-tight">FIDEM</span>
          </div>
          <LangSwitch />
        </div>

        {/* Premium card */}
        <div className="card-premium p-6 sm:p-7 stagger">
          <div className="inline-flex items-center gap-1.5 text-[11px] tracking-wider uppercase font-semibold text-foreground bg-primary/10 px-3 py-1 rounded-full">
            <Sparkles className="w-3 h-3" /> {t("safe_search") || "Premium"}
          </div>

          <h1 className="mt-4 font-heading text-3xl sm:text-4xl tracking-tight font-semibold leading-[1.05]">
            {t("welcome")}.
          </h1>
          <p className="text-muted-foreground mt-2 text-sm sm:text-base leading-relaxed">
            {t("tagline")}
          </p>

          {/* Mode switcher (segmented) */}
          <div className="mt-6 inline-flex p-1 rounded-2xl bg-muted/60 border border-border w-full">
            <button
              data-testid="btn-mode-login"
              onClick={() => setMode("login")}
              className={`flex-1 py-2 text-sm font-medium rounded-xl transition ${
                mode === "login" ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {t("login")}
            </button>
            <button
              data-testid="btn-mode-register"
              onClick={() => setMode("register")}
              className={`flex-1 py-2 text-sm font-medium rounded-xl transition ${
                mode === "register" ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {t("register")}
            </button>
            {/* legacy toggle kept for tests */}
            <button
              data-testid="btn-toggle-mode"
              onClick={() => setMode((m) => (m === "login" ? "register" : "login"))}
              className="hidden"
            />
          </div>

          <form onSubmit={submit} className="mt-5 space-y-3" data-testid="auth-form">
            {mode === "register" && (
              <div className="relative">
                <UserIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  data-testid="input-name"
                  type="text"
                  placeholder={t("name")}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="input !pl-11"
                />
              </div>
            )}
            <div className="relative">
              <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                data-testid="input-email"
                type="email"
                required
                placeholder={t("email")}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input !pl-11"
              />
            </div>
            <div className="relative">
              <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                data-testid="input-password"
                type={showPwd ? "text" : "password"}
                required
                placeholder={t("password")}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input !pl-11 !pr-16"
              />
              <button
                type="button"
                onClick={() => setShowPwd((s) => !s)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[11px] uppercase tracking-wider font-medium text-muted-foreground hover:text-foreground transition"
              >
                {showPwd ? "Hide" : "Show"}
              </button>
            </div>

            <button
              data-testid="btn-submit"
              type="submit"
              disabled={loading}
              className="btn-primary mt-2"
            >
              {loading ? (
                <span className="inline-block w-4 h-4 rounded-full border-2 border-white/60 border-t-transparent animate-spin" />
              ) : (
                <>
                  {mode === "login" ? t("login") : t("register")}
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          <div className="divider-with-label my-5">
            <span>{t("continue_with_tg") ? "or" : "or"}</span>
          </div>

          <button
            data-testid="btn-telegram-login"
            onClick={tryTelegram}
            disabled={loading}
            className="btn-secondary"
          >
            <Send className="w-4 h-4" /> {t("continue_with_tg")}
          </button>

          {/* Trust strip */}
          <div className="mt-6 flex items-center justify-center gap-2 text-[11px] text-muted-foreground">
            <ShieldCheck className="w-3.5 h-3.5 text-secondary" />
            <span>{t("safe_search") || "Verified · AI Match · Privacy-first"}</span>
          </div>
        </div>

        {/* Feature mini grid */}
        <div className="mt-6 grid grid-cols-3 gap-2 text-center">
          <MiniFeat label={t("verified") || "Verified"} value="ID + Selfie" />
          <MiniFeat label={t("ai") || "AI"} value="Big5 + 30" />
          <MiniFeat label={t("privacy") || "Privacy"} value="Photo blur" />
        </div>

        <p className="mt-auto text-[11px] text-muted-foreground text-center pt-8">
          © FIDEM · {new Date().getFullYear()}
        </p>
      </div>
    </div>
  );
}

function MiniFeat({ label, value }) {
  return (
    <div className="rounded-2xl bg-card/70 border border-border px-2 py-3 backdrop-blur-sm">
      <div className="text-[10px] uppercase tracking-wider font-semibold text-muted-foreground">{label}</div>
      <div className="text-xs font-medium mt-0.5">{value}</div>
    </div>
  );
}
