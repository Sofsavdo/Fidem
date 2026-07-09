import React, { useId, useState } from "react";

// Romantic hero illustration: two silhouettes at sunset raising their hands
// into a shared heart with the sun glowing inside it - modelled on the
// reference photo the founder picked, but drawn as brand-safe vector art so
// it ships inside the bundle (no CDN, no ethnicity, always loads).
//
// If a real photo is dropped at public/<photo> (default /welcome-hero.jpg),
// it renders on top of the scene automatically.
export default function HeroScene({ className = "", photo = "/welcome-hero.jpg" }) {
  const id = useId();
  const [photoOk, setPhotoOk] = useState(true);
  return (
    // NOTE: no `relative` here - callers pass their own positioning (usually
    // "absolute inset-0"), and a hardcoded `relative` would fight it and
    // collapse the box to zero height.
    <div className={`overflow-hidden ${className}`}>
      <svg viewBox="0 0 100 140" preserveAspectRatio="xMidYMid slice" className="absolute inset-0 w-full h-full" aria-hidden="true">
        <defs>
          <linearGradient id={`sky-${id}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#FFB3CF" />
            <stop offset="0.45" stopColor="#FF8E7A" />
            <stop offset="1" stopColor="#FFC46B" />
          </linearGradient>
          <linearGradient id={`sea-${id}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#E8756E" />
            <stop offset="1" stopColor="#5C2450" />
          </linearGradient>
          <radialGradient id={`sun-${id}`}>
            <stop offset="0" stopColor="#FFFBEA" />
            <stop offset="0.55" stopColor="#FFE9A8" />
            <stop offset="1" stopColor="#FFC46B" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* sky + sea */}
        <rect x="0" y="0" width="100" height="96" fill={`url(#sky-${id})`} />
        <rect x="0" y="96" width="100" height="44" fill={`url(#sea-${id})`} />
        {/* sun reflection on the water */}
        <rect x="42" y="96" width="16" height="44" fill="#FFD98A" opacity="0.3" />
        <rect x="46" y="96" width="8" height="44" fill="#FFEDC2" opacity="0.35" />

        {/* the sun, held inside the heart */}
        <circle cx="50" cy="47" r="24" fill={`url(#sun-${id})`} />
        <circle cx="50" cy="47" r="10.5" fill="#FFF6DC" />

        {/* heart formed by the couple's hands */}
        <path
          d="M50 60 C41 52.5 35 48 35 40.5 C35 35 39.5 32 44 34 C47 35.3 49 38 50 40.5 C51 38 53 35.3 56 34 C60.5 32 65 35 65 40.5 C65 48 59 52.5 50 60 Z"
          fill="none" stroke="#331030" strokeWidth="4.6" strokeLinejoin="round"
        />
        {/* arms reaching up to the heart */}
        <path d="M34 82 C36 71 40 62 45.5 57" fill="none" stroke="#331030" strokeWidth="5.6" strokeLinecap="round" />
        <path d="M66 82 C64 71 60 62 54.5 57" fill="none" stroke="#331030" strokeWidth="5.6" strokeLinecap="round" />

        {/* the couple: two silhouettes, close together */}
        <path
          d="M0 140 L0 104 C6 102 10 96 13 88 C15 76 19 68 26 68 C33 68 37 76 39 86 C41.5 94 45 99 50 101 C55 99 58.5 94 61 86 C63 76 67 68 74 68 C81 68 85 76 87 88 C90 96 94 102 100 104 L100 140 Z"
          fill="#331030"
        />
        {/* heads */}
        <circle cx="26" cy="59" r="9.2" fill="#331030" />
        <circle cx="74" cy="59" r="9.2" fill="#331030" />

        {/* sparkles */}
        <circle cx="16" cy="22" r="1.1" fill="#fff" opacity="0.7" />
        <circle cx="84" cy="16" r="0.9" fill="#fff" opacity="0.6" />
        <circle cx="74" cy="30" r="0.7" fill="#fff" opacity="0.5" />
        <circle cx="24" cy="38" r="0.8" fill="#fff" opacity="0.5" />
      </svg>

      {photoOk && (
        <img
          src={photo}
          alt=""
          onError={() => setPhotoOk(false)}
          className="absolute inset-0 w-full h-full object-cover"
        />
      )}
    </div>
  );
}
