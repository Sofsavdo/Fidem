import React from "react";
import { NavLink } from "react-router-dom";
import { Users, MessageCircle, Bookmark, User, Wallet, Gift } from "lucide-react";
import { useApp } from "@/contexts/AppContext";
import { selection } from "@/lib/haptics";

const tabs = [
  { to: "/", icon: Users, key: "candidates", testid: "nav-candidates" },
  { to: "/messages", icon: MessageCircle, key: "messages", testid: "nav-messages" },
  { to: "/withdrawals", icon: Wallet, key: "balance", testid: "nav-balance" },
  { to: "/saved", icon: Bookmark, key: "saved", testid: "nav-saved" },
  { to: "/me", icon: User, key: "me", testid: "nav-me" },
];

export default function BottomNav() {
  const { t } = useApp();
  return (
    <nav
      data-testid="bottom-nav"
      className="fixed bottom-0 inset-x-0 glass border-t border-border/60 pb-[env(safe-area-inset-bottom)]"
      style={{ zIndex: 10000 }}
    >
      <div className="max-w-md mx-auto grid grid-cols-5">
        {tabs.map((tab) => (
          <NavLink
            key={tab.key}
            to={tab.to}
            data-testid={tab.testid}
            end={tab.to === "/"}
            onClick={selection}
            className={({ isActive }) =>
              `flex flex-col items-center gap-0.5 py-2.5 transition-colors ${
                isActive ? "text-primary" : "text-muted-foreground hover:text-foreground"
              }`
            }
          >
            {({ isActive }) => (
              <>
                <tab.icon className="w-5 h-5" strokeWidth={isActive ? 2.4 : 1.8} />
                <span className={`text-[10px] tracking-wide ${isActive ? "font-medium" : ""}`}>
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
