import React, { useEffect, useState } from "react";

// Fills its (relatively positioned) parent with a profile photo. When there is
// no photo - or it fails to load - it shows a neutral initial-letter tile
// instead of a stock picture or the browser's broken-image alt text (which used
// to print the person's name on top of the match badge).
export default function PhotoFill({ src, name, className = "" }) {
  const [broken, setBroken] = useState(false);
  useEffect(() => { setBroken(false); }, [src]);
  const initial = (name || "?").trim().charAt(0).toUpperCase() || "?";
  const show = !!src && !broken;
  return (
    <>
      <div
        aria-hidden="true"
        className="absolute inset-0 grid place-items-center bg-gradient-to-br from-primary/15 via-muted to-secondary/15 text-primary/60 font-heading font-semibold text-5xl select-none"
      >
        {initial}
      </div>
      {show && (
        <img
          src={src}
          alt=""
          loading="lazy"
          decoding="async"
          onError={() => setBroken(true)}
          className={`absolute inset-0 w-full h-full object-cover ${className}`}
        />
      )}
    </>
  );
}
