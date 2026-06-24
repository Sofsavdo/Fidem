import React from "react";
import BottomNav from "@/components/BottomNav";
import { Outlet } from "react-router-dom";

export default function Layout() {
  return (
    <div className="min-h-screen bg-background bg-grain">
      <div className="max-w-md mx-auto pb-24 min-h-screen relative">
        <Outlet />
      </div>
      <BottomNav />
    </div>
  );
}
