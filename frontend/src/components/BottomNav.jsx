import React from "react";
import { NavLink } from "react-router-dom";
import { Users, MessageCircle, Heart, User, Megaphone, Gift } from "lucide-react";
import { useApp } from "@/contexts/AppContext";
import { useAnnouncements } from "@/hooks/queries";
import { selection } from "@/lib/haptics";

// The middle tab is Anonslar (news feed) — balance/top-up lives on the Me
// page, since not everyone touches money but everyone can follow news.
const tabs = [
  { to: "/", icon: Users, key: "candidates", testid: "nav-candidates" },
  { to: "/messages", icon: MessageCircle, key: "messages", testid: "nav-messages" },
  { to: "/announcements", icon: Megaphone, key: "anons", testid: "nav-anons" },
  { to: "/saved", icon: Heart, key: "liked", testid: "nav-saved" },
  { to: "/gifts", icon: Gift, key: "gift", testid: "nav-gift" },
  { to: "/me", icon: User, key: "me", testid: "nav-me" },
];

export default function BottomNav() {
  const { t } = useApp();
  // Unread dot: latest announcement newer than the last one the user opened.
  const { data: anons = [] } = useAnnouncements();
  let hasNewAnons = false;
  try {
    const latest = anons[0]?.created_at || "";
    hasNewAnons = !!latest && latest > (localStorage.getItem("fidem_anons_seen") || "");
  } catch { /* ignore */ }
  return (
    <nav
      data-testid="bottom-nav"
      className="shrink-0 glass border-t border-border/60 pb-[env(safe-area-inset-bottom)]"
      style={{ zIndex: 10000 }}
    >
      <div className="max-w-md mx-auto grid grid-cols-6 px-1 pt-1.5">
        {tabs.map((tab) => (
          <NavLink
            key={tab.key}
            to={tab.to}
            data-testid={tab.testid}
            end={tab.to === "/"}
            onClick={selection}
            className="flex flex-col items-center justify-center py-1.5"
          >
            {({ isActive }) => (
              <>
                <span
                  className={`relative grid place-items-center w-11 h-8 rounded-2xl transition-all duration-200 ${
                    isActive ? "bg-primary/12 text-primary" : "text-muted-foreground"
                  }`}
                >
                  <tab.icon className="w-[22px] h-[22px]" strokeWidth={isActive ? 2.4 : 1.8} />
                  {tab.key === "anons" && hasNewAnons && (
                    <span data-testid="anons-dot" className="absolute top-0.5 right-1.5 w-2 h-2 rounded-full bg-primary" />
                  )}
                </span>
                <span
                  className={`text-[10px] tracking-wide mt-0.5 transition-colors ${
                    isActive ? "text-primary font-semibold" : "text-muted-foreground"
                  }`}
                >
                  {t(tab.key)}
                </span>
              </>
            )}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
