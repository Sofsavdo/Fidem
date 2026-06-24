import React from "react";
import { NavLink } from "react-router-dom";
import { Users, MessageCircle, Bookmark, User } from "lucide-react";
import { useApp } from "@/contexts/AppContext";

const tabs = [
  { to: "/", icon: Users, key: "candidates", testid: "nav-candidates" },
  { to: "/messages", icon: MessageCircle, key: "messages", testid: "nav-messages" },
  { to: "/saved", icon: Bookmark, key: "saved", testid: "nav-saved" },
  { to: "/me", icon: User, key: "me", testid: "nav-me" },
];

export default function BottomNav() {
  const { t } = useApp();
  return (
    <nav
      data-testid="bottom-nav"
      className="fixed bottom-0 inset-x-0 z-40 glass border-t border-border/60 pb-[env(safe-area-inset-bottom)]"
    >
      <div className="max-w-md mx-auto grid grid-cols-4">
        {tabs.map((tab) => (
          <NavLink
            key={tab.key}
            to={tab.to}
            data-testid={tab.testid}
            end={tab.to === "/"}
            className={({ isActive }) =>
              `flex flex-col items-center gap-1 py-3 transition-colors ${
                isActive ? "text-primary" : "text-muted-foreground hover:text-foreground"
              }`
            }
          >
            {({ isActive }) => (
              <>
                <tab.icon className="w-5 h-5" strokeWidth={isActive ? 2.4 : 1.8} />
                <span className={`text-[11px] tracking-wide ${isActive ? "font-medium" : ""}`}>
                  {t(tab.key)}
                </span>
                {isActive && <span className="w-1 h-1 rounded-full bg-primary -mt-0.5" />}
              </>
            )}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
