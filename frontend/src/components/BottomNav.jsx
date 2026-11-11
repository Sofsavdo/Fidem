import React from "react";
import { NavLink } from "react-router-dom";
import { Users, MessageCircle, Heart, User } from "lucide-react";
import { useApp } from "@/contexts/AppContext";
import { selection } from "@/lib/haptics";

// Four tabs keep the core loop obvious: candidates -> chats -> interests ->
// profile. Announcements and the gift shop live on the Me page.
const tabs = [
  { to: "/", icon: Users, key: "candidates", testid: "nav-candidates" },
  { to: "/messages", icon: MessageCircle, key: "messages", testid: "nav-messages" },
  { to: "/saved", icon: Heart, key: "liked", testid: "nav-saved" },
  { to: "/me", icon: User, key: "me", testid: "nav-me" },
];

export default function BottomNav() {
  const { t } = useApp();
  return (
    <nav
      data-testid="bottom-nav"
      className="shrink-0 glass border-t border-border/60 pb-[env(safe-area-inset-bottom)]"
      style={{ zIndex: 10000 }}
    >
      <div className="max-w-md mx-auto grid grid-cols-4 px-1 pt-1.5">
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
