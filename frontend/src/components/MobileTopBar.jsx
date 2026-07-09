import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Bell, Crown, Wallet, Sun, Moon } from "lucide-react";
import Logo from "@/components/Logo";
import { useApp } from "@/contexts/AppContext";
import { getTheme, setTheme, effectiveIsDark } from "@/lib/theme";

// Cycles system -> light -> dark -> system. The icon always reflects the
// *effective* (rendered) mode, so a "system" pick that resolves to dark
// still shows the moon — what you see is what you get, no hidden state.
function ThemeToggle() {
  const [theme, setThemeState] = useState(getTheme());
  const isDark = effectiveIsDark(theme);
  const cycle = () => {
    const next = theme === "system" ? (effectiveIsDark("system") ? "light" : "dark") : theme === "light" ? "dark" : "system";
    setThemeState(next);
    setTheme(next);
  };
  return (
    <button
      data-testid="topbar-theme"
      onClick={cycle}
      className="p-2 rounded-full hover:bg-muted"
      title="Theme"
    >
      {isDark ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
    </button>
  );
}

export default function MobileTopBar() {
  const { user, lang, setLang, t } = useApp();
  const nav = useNavigate();
  if (!user) return null;
  const balance = user.balance || 0;
  return (
    <header data-testid="mobile-topbar" className="sticky top-0 z-30 glass border-b border-border/40 px-3 py-2 flex items-center justify-between gap-2" style={{ paddingTop: "max(8px, env(safe-area-inset-top))" }}>
      <Link to="/" className="flex items-center gap-2">
        <Logo className="w-8 h-8" />
        <span className="font-heading font-semibold text-lg leading-none tracking-tight">FIDEM</span>
      </Link>
      <div className="flex items-center gap-1">
        {/* Unified wallet pill → balance/top-up surface (in-app spending money).
            Shows balance and (only if > 0) coins side-by-side inside one button */}
        <button
          data-testid="topbar-balance"
          onClick={() => nav("/premium?tab=balance")}
          className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-full bg-muted/60 hover:bg-muted text-xs font-medium"
          title="Wallet"
        >
          <Wallet className="w-3.5 h-3.5 text-foreground" />
          <span>{balance.toLocaleString()} {t("sum")}</span>
        </button>
        {user.plan === "vip" && (
          <span className="inline-flex items-center gap-0.5 px-2 py-1 rounded-full bg-gold-light/60 text-gold-dark text-[10px] font-medium">
            <Crown className="w-3 h-3" /> VIP
          </span>
        )}
        <button
          data-testid="topbar-lang"
          onClick={() => {
            const order = ["uz", "ru", "en"];
            const cur = order.indexOf(lang);
            setLang(order[(cur + 1) % 3]);
          }}
          className="px-2 py-1.5 rounded-full bg-muted/60 text-[11px] font-medium uppercase"
        >
          {lang}
        </button>
        <ThemeToggle />
        <Link to="/notifications" data-testid="topbar-notif" className="p-2 rounded-full hover:bg-muted">
          <Bell className="w-5 h-5" />
        </Link>
      </div>
    </header>
  );
}
