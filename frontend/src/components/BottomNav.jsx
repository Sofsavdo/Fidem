import React from "react";
import { NavLink } from "react-router-dom";
import { Users, MessageCircle, Heart, User, Wallet } from "lucide-react";
import { useApp } from "@/contexts/AppContext";
import { selection } from "@/lib/haptics";

// Balance tab points at the top-up/balance surface (not withdrawals) — app
// balance is for in-app purchases; withdrawals live inside the money group.
const tabs = [
  { to: "/", icon: Users, key: "candidates", testid: "nav-candidates" },
  { to: "/messages", icon: MessageCircle, key: "messages", testid: "nav-messages" },
  { to: "/premium?tab=balance", icon: Wallet, key: "balance", testid: "nav-balance" },
  { to: "/saved", icon: Heart, key: "liked", testid: "nav-saved" },
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
      <div className="max-w-md mx-auto grid grid-cols-5 px-1.5 pt-1.5">
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
                  className={`grid place-items-center w-11 h-8 rounded-2xl transition-all duration-200 ${
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
