import React from "react";
import { Heart } from "lucide-react";

// Premium boot/loading state — a gently breathing FIDEM mark with a soft
// expanding ring. Replaces the plain spinner + "loading" text so first paint
// feels like a native app splash, not a web page fetching.
export default function BrandSplash({ full = true }) {
  return (
    <div className={`${full ? "min-h-[100dvh]" : "min-h-[50vh]"} grid place-items-center bg-background`} data-testid="brand-splash">
      <div className="relative grid place-items-center">
        <span className="absolute w-16 h-16 rounded-3xl bg-primary/25 animate-ping" style={{ animationDuration: "1.6s" }} />
        <span className="absolute w-24 h-24 rounded-full bg-gradient-to-br from-primary/10 to-gold/10 blur-xl" />
        <div className="relative w-16 h-16 rounded-3xl bg-gradient-to-br from-primary to-gold grid place-items-center shadow-lg shadow-primary/30 animate-brandpulse">
          <Heart className="w-8 h-8 text-white" fill="currentColor" />
        </div>
      </div>
    </div>
  );
}
