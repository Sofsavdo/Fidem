import React from "react";
import BottomNav from "@/components/BottomNav";
import DailyCheckIn from "@/components/DailyCheckIn";
import MobileTopBar from "@/components/MobileTopBar";
import OfflineBanner from "@/components/OfflineBanner";
import MatchCelebration from "@/components/MatchCelebration";
import { Outlet, useLocation } from "react-router-dom";

export default function Layout({ children }) {
  const location = useLocation();
  const isAdmin = location.pathname.startsWith("/admin");
  const isChat = location.pathname.startsWith("/chat/");
  
  // Admin pages have their own layout, bypass Layout entirely
  if (isAdmin) {
    return (
      <div className="min-h-screen bg-background bg-grain">
        <OfflineBanner />
        {children || <Outlet />}
      </div>
    );
  }
  
  // Mobile-first: sidebar only shown on admin pages.
  // App-shell layout: the outer frame is pinned to the viewport height and
  // never scrolls itself — only #app-scroll (the content area) scrolls. This
  // keeps the bottom nav a normal (non-fixed) flex child that physically
  // cannot move during scroll, sidestepping the WebView/iOS jitter that
  // `position: fixed` bottom bars are prone to inside Telegram's in-app browser.
  return (
    <div className="h-[100dvh] flex flex-col bg-background bg-grain overflow-hidden">
      <OfflineBanner />
      {!isAdmin && !isChat && <MobileTopBar />}
      <main id="app-scroll" className="flex-1 min-h-0 overflow-y-auto overscroll-contain" style={{ WebkitOverflowScrolling: "touch" }}>
        <div className={`max-w-2xl xl:max-w-3xl mx-auto ${isChat ? "pb-0" : "pb-6 md:pb-10"} relative`}>
          {children || <Outlet />}
        </div>
      </main>
      {!isChat && <BottomNav />}
      {!isChat && <DailyCheckIn />}
      <MatchCelebration />
    </div>
  );
}
