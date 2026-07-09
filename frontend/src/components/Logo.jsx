import React, { useId } from "react";

// FIDEM brand mark — an "infinity heart": two ribbon loops that meet at a heart
// tip. Pure SVG, crisp at any size. Two-tone magenta→purple to match the brand.
//
//   tone="gradient" (default) — magenta (left) + purple (right), for light bg
//   tone="white"              — solid white, for coloured/gradient surfaces
//   tone="mono"               — currentColor
const LEFT = "M50 80 C 30 60, 12 52, 15 33 C 17 21, 37 20, 46 35 C 49 40, 50 45, 50 45";
const RIGHT = "M50 80 C 70 60, 88 52, 85 33 C 83 21, 63 20, 54 35 C 51 40, 50 45, 50 45";

export default function Logo({ className = "w-8 h-8", tone = "gradient", title = "FIDEM" }) {
  const id = useId();
  const leftStroke = tone === "white" ? "#fff" : tone === "mono" ? "currentColor" : `url(#l-${id})`;
  const rightStroke = tone === "white" ? "#fff" : tone === "mono" ? "currentColor" : `url(#r-${id})`;
  return (
    <svg viewBox="0 0 100 100" className={className} fill="none" role="img" aria-label={title} xmlns="http://www.w3.org/2000/svg">
      {tone === "gradient" && (
        <defs>
          <linearGradient id={`l-${id}`} x1="12" y1="20" x2="50" y2="80" gradientUnits="userSpaceOnUse">
            <stop stopColor="#FF3DAE" /><stop offset="1" stopColor="#F0269D" />
          </linearGradient>
          <linearGradient id={`r-${id}`} x1="88" y1="20" x2="50" y2="80" gradientUnits="userSpaceOnUse">
            <stop stopColor="#9B4DFF" /><stop offset="1" stopColor="#8A2BE2" />
          </linearGradient>
        </defs>
      )}
      <g strokeWidth="15" strokeLinecap="round">
        <path d={LEFT} stroke={leftStroke} />
        <path d={RIGHT} stroke={rightStroke} />
      </g>
    </svg>
  );
}

// Rounded app-icon badge: the white mark on the brand gradient.
export function LogoBadge({ className = "w-16 h-16" }) {
  return (
    <div className={`${className} rounded-[28%] bg-gradient-to-br from-[#F0269D] to-[#8A2BE2] grid place-items-center shadow-lg shadow-[#8A2BE2]/30`}>
      <Logo tone="white" className="w-[64%] h-[64%]" />
    </div>
  );
}
