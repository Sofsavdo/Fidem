import React, { useId } from "react";

// FIDEM brand mark — a ribbon "infinity" (endless connection) in the brand
// magenta→purple gradient. Pure SVG so it stays crisp at every size and can be
// tinted. Use this everywhere instead of a heart emoji or raster logo.
//
//   tone="gradient" (default) — magenta→purple, for light surfaces
//   tone="white"              — solid white, for coloured/gradient surfaces
//   tone="mono"               — currentColor, inherits text colour
export default function Logo({ className = "w-8 h-8", tone = "gradient", title = "FIDEM" }) {
  const id = useId();
  const stroke = tone === "white" ? "#fff" : tone === "mono" ? "currentColor" : `url(#fidem-${id})`;
  return (
    <svg viewBox="0 0 100 100" className={className} fill="none" role="img" aria-label={title} xmlns="http://www.w3.org/2000/svg">
      {tone === "gradient" && (
        <defs>
          <linearGradient id={`fidem-${id}`} x1="12" y1="26" x2="88" y2="74" gradientUnits="userSpaceOnUse">
            <stop stopColor="#F0269D" />
            <stop offset="1" stopColor="#8A2BE2" />
          </linearGradient>
        </defs>
      )}
      <path
        d="M50 50 C 40 26, 12 28, 12 50 C 12 72, 40 74, 50 50 C 60 26, 88 28, 88 50 C 88 72, 60 74, 50 50 Z"
        stroke={stroke}
        strokeWidth="14"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// The rounded app-icon badge: the white mark on the brand gradient. Used for
// the boot splash and anywhere a "logo tile" is wanted.
export function LogoBadge({ className = "w-16 h-16" }) {
  return (
    <div className={`${className} rounded-[28%] bg-gradient-to-br from-[#F0269D] to-[#8A2BE2] grid place-items-center shadow-lg shadow-[#8A2BE2]/30`}>
      <Logo tone="white" className="w-[62%] h-[62%]" />
    </div>
  );
}
