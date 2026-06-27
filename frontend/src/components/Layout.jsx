import React from "react";
import BottomNav from "@/components/BottomNav";
import Sidebar from "@/components/Sidebar";
import DailyCheckIn from "@/components/DailyCheckIn";
import { Outlet } from "react-router-dom";

export default function Layout() {
  return (
    <div className="min-h-screen bg-background bg-grain">
      <Sidebar />
      <main className="md:pl-64 lg:pl-72">
        <div className="max-w-2xl xl:max-w-3xl mx-auto pb-24 md:pb-10 min-h-screen relative">
          <Outlet />
        </div>
      </main>
      <BottomNav />
      <DailyCheckIn />
    </div>
  );
}
