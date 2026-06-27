import React from "react";
import BottomNav from "@/components/BottomNav";
import Sidebar from "@/components/Sidebar";
import DailyCheckIn from "@/components/DailyCheckIn";
import MobileTopBar from "@/components/MobileTopBar";
import OfflineBanner from "@/components/OfflineBanner";
import { Outlet, useLocation } from "react-router-dom";

export default function Layout({ children }) {
  const location = useLocation();
  const isAdmin = location.pathname.startsWith("/admin");
  const isChat = location.pathname.startsWith("/chat/");
  // Mobile-first: sidebar only shown on admin pages
  return (
    <div className="min-h-screen bg-background bg-grain">
      <OfflineBanner />
      {isAdmin && <Sidebar />}
      {!isAdmin && !isChat && <MobileTopBar />}
      <main className={isAdmin ? "md:pl-64 lg:pl-72" : ""}>
        <div className={`max-w-2xl xl:max-w-3xl mx-auto ${isChat ? "pb-0" : "pb-24 md:pb-10"} min-h-screen relative`}>
          {children || <Outlet />}
        </div>
      </main>
      {!isChat && <BottomNav />}
      {!isChat && <DailyCheckIn />}
    </div>
  );
}
