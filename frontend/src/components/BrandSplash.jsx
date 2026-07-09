import React from "react";
import logo from "@/assets/fidem-logo-256.png";

// Premium boot/loading state — the FIDEM logo gently breathing with a soft
// glow. Replaces the plain spinner + "loading" text so first paint feels like
// a native app splash.
export default function BrandSplash({ full = true }) {
  return (
    <div className={`${full ? "min-h-[100dvh]" : "min-h-[50vh]"} grid place-items-center bg-background`} data-testid="brand-splash">
      <div className="relative grid place-items-center">
        <span className="absolute w-28 h-28 rounded-full bg-[#C026A6]/20 blur-2xl animate-brandpulse" />
        <img src={logo} alt="FIDEM" className="relative w-20 h-20 rounded-3xl shadow-lg animate-brandpulse" />
      </div>
    </div>
  );
}
