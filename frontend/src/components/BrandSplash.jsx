import React from "react";
import { LogoBadge } from "@/components/Logo";

// Premium boot/loading state — the FIDEM brand mark gently breathing with a
// soft glow. Replaces the plain spinner + "loading" text.
export default function BrandSplash({ full = true }) {
  return (
    <div className={`${full ? "min-h-[100dvh]" : "min-h-[50vh]"} grid place-items-center bg-background`} data-testid="brand-splash">
      <div className="relative grid place-items-center">
        <span className="absolute w-28 h-28 rounded-full bg-primary/25 blur-2xl animate-brandpulse" />
        <LogoBadge className="relative w-20 h-20 animate-brandpulse" />
      </div>
    </div>
  );
}
