import React from "react";
import { LogoBadge } from "@/components/Logo";

// Premium boot/loading state — the FIDEM mark draws itself in a seamless loop
// (a faint full logo is always visible, so it shows instantly and never looks
// half-finished regardless of how fast/slow the app loads).
export default function BrandSplash({ full = true }) {
  return (
    <div className={`${full ? "min-h-[100dvh]" : "min-h-[50vh]"} grid place-items-center bg-background`} data-testid="brand-splash">
      <div className="relative grid place-items-center">
        <span className="absolute w-28 h-28 rounded-full bg-primary/20 blur-2xl animate-brandpulse" />
        <LogoBadge animated className="relative w-20 h-20" />
      </div>
    </div>
  );
}
