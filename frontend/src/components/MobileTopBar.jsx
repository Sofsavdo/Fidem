import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { Bell, Crown, Wallet } from "lucide-react";
import { useApp } from "@/contexts/AppContext";

export default function MobileTopBar() {
  const { user, lang, setLang } = useApp();
  const nav = useNavigate();
  if (!user) return null;
  const balance = user.balance || 0;
  const coins = user.coins || 0;
  return (
    <header data-testid="mobile-topbar" className="sticky top-0 z-30 glass border-b border-border/40 px-3 py-2 flex items-center justify-between gap-2" style={{ paddingTop: "max(8px, env(safe-area-inset-top))" }}>
      <Link to="/" className="flex items-center gap-2">
        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-primary to-secondary grid place-items-center text-white text-base">
          ❤️
        </div>
        <span className="font-heading font-semibold text-lg leading-none">FIDEM</span>
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
          <span>{balance.toLocaleString()}</span>
          {coins > 0 && (
            <>
              <span className="opacity-30 mx-0.5">·</span>
              <span className="inline-flex items-center gap-0.5 text-gold-dark" data-testid="topbar-coins">
                🪙 {coins.toLocaleString()}
              </span>
            </>
          )}
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
        <Link to="/notifications" data-testid="topbar-notif" className="p-2 rounded-full hover:bg-muted">
          <Bell className="w-5 h-5" />
        </Link>
      </div>
    </header>
  );
}
