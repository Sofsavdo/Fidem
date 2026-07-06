import React from "react";
import { NavLink, Link } from "react-router-dom";
import { Users, MessageCircle, Bookmark, User, Heart, Sparkles, Crown, Gift, ShieldCheck, Brain, UsersRound, Pen, BookOpen, Wallet, Phone } from "lucide-react";
import { useApp } from "@/contexts/AppContext";
import { PlanPill } from "@/components/Badges";
import { photoSrc } from "@/lib/photo";

const tabs = [
  { to: "/", icon: Users, key: "candidates", testid: "nav-candidates" },
  { to: "/messages", icon: MessageCircle, key: "messages", testid: "nav-messages" },
  { to: "/saved", icon: Bookmark, key: "saved", testid: "nav-saved" },
  { to: "/me", icon: User, key: "me", testid: "nav-me" },
];

export default function Sidebar() {
  const { t, user } = useApp();
  if (!user) return null;
  return (
    <aside data-testid="sidebar" className="hidden md:flex md:flex-col md:fixed md:left-0 md:top-0 md:h-screen md:w-64 lg:w-72 border-r border-border/60 bg-card/30 backdrop-blur z-30">
      <div className="px-5 pt-6 pb-4 flex items-center gap-2">
        <div className="w-9 h-9 rounded-2xl bg-primary text-white grid place-items-center">
          <Heart className="w-4 h-4" fill="currentColor" />
        </div>
        <span className="font-heading text-xl font-semibold tracking-tight">FIDEM</span>
      </div>

      <Link to="/me" className="mx-3 mb-4 rounded-2xl p-3 hover:bg-muted transition flex items-center gap-3" data-testid="sidebar-me">
        <div className="w-10 h-10 rounded-xl bg-muted overflow-hidden">
          {user.photo_url ? (
            <img loading="lazy" decoding="async" src={photoSrc(user.photo_url)} alt="" className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full grid place-items-center text-muted-foreground text-sm">{user.name?.[0]}</div>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <p className="text-sm font-medium truncate">{user.name}</p>
            <PlanPill plan={user.plan} />
          </div>
          <p className="text-[11px] text-muted-foreground">{(user.balance || 0).toLocaleString()} so'm</p>
        </div>
      </Link>

      <nav className="flex-1 px-3 space-y-1">
        {tabs.map((tab) => (
          <NavLink
            key={tab.key}
            to={tab.to}
            data-testid={`side-${tab.testid}`}
            end={tab.to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-2xl px-4 py-2.5 text-sm transition ${
                isActive ? "bg-primary text-white" : "text-foreground hover:bg-muted"
              }`
            }
          >
            <tab.icon className="w-4 h-4" />
            <span>{t(tab.key) === tab.key ? t(tab.key.replace("_short", "")) : t(tab.key)}</span>
          </NavLink>
        ))}
        <Link to="/premium?tab=plans" data-testid="side-premium" className="flex items-center gap-3 rounded-2xl px-4 py-2.5 text-sm hover:bg-muted text-foreground">
          <Crown className="w-4 h-4 text-gold-dark" />
          <span>{t("premium")}</span>
        </Link>
        <Link to="/personality" data-testid="side-personality" className="flex items-center gap-3 rounded-2xl px-4 py-2.5 text-sm hover:bg-muted text-foreground">
          <Brain className="w-4 h-4 text-secondary" />
          <span>{t("personality_test")}</span>
        </Link>
        <Link to="/prompts" data-testid="side-prompts" className="flex items-center gap-3 rounded-2xl px-4 py-2.5 text-sm hover:bg-muted text-foreground">
          <Pen className="w-4 h-4 text-secondary" />
          <span>{t("profile_prompts")}</span>
        </Link>
        <Link to="/stories" data-testid="side-stories" className="flex items-center gap-3 rounded-2xl px-4 py-2.5 text-sm hover:bg-muted text-foreground">
          <BookOpen className="w-4 h-4 text-foreground" />
          <span>{t("success_stories")}</span>
        </Link>
        <Link to="/boost" data-testid="side-boost" className="flex items-center gap-3 rounded-2xl px-4 py-2.5 text-sm hover:bg-muted text-foreground">
          <Sparkles className="w-4 h-4 text-foreground" />
          <span>{t("boost_title")}</span>
        </Link>
        <Link to="/concierge" data-testid="side-concierge" className="flex items-center gap-3 rounded-2xl px-4 py-2.5 text-sm hover:bg-muted text-foreground">
          <Crown className="w-4 h-4 text-secondary" />
          <span>{t("concierge_title")}</span>
        </Link>
        <Link to="/family" data-testid="side-family" className="flex items-center gap-3 rounded-2xl px-4 py-2.5 text-sm hover:bg-muted text-foreground">
          <Phone className="w-4 h-4 text-foreground" />
          <span>{t("family_contact")}</span>
        </Link>
        <Link to="/withdrawals" data-testid="side-withdrawals" className="flex items-center gap-3 rounded-2xl px-4 py-2.5 text-sm hover:bg-muted text-foreground">
          <Wallet className="w-4 h-4 text-foreground" />
          <span>{t("withdraw_money")}</span>
        </Link>
        <Link to="/notifications" data-testid="side-notif" className="flex items-center gap-3 rounded-2xl px-4 py-2.5 text-sm hover:bg-muted text-foreground">
          <Gift className="w-4 h-4" />
          <span>{t("notifications")}</span>
        </Link>
        {user.is_admin && (
          <Link to="/admin" data-testid="side-admin" className="flex items-center gap-3 rounded-2xl px-4 py-2.5 text-sm hover:bg-muted text-foreground">
            <ShieldCheck className="w-4 h-4" />
            <span>{t("admin_panel")}</span>
          </Link>
        )}
      </nav>

      <div className="px-5 py-4 text-[11px] text-muted-foreground border-t border-border/60">
        FIDEM · {t("tagline")}
      </div>
    </aside>
  );
}
