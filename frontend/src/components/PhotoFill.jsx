import React, { useEffect, useState } from "react";

// Fills its (relatively positioned) parent with a profile photo. While it loads
// - or if it fails - a plain neutral tile stays behind it, and the browser's
// broken-image icon / alt text (which used to print the person's name on top of
// the match badge) never shows.
// contain: show the WHOLE photo (nothing cut off at the top or bottom); the
// empty space around it is filled with a blurred copy of the same photo.
export default function PhotoFill({ src, className = "", contain = false }) {
  const [broken, setBroken] = useState(false);
  useEffect(() => { setBroken(false); }, [src]);
  const show = !!src && !broken;
  return (
    <>
      <div aria-hidden="true" className="absolute inset-0 bg-gradient-to-br from-muted via-muted to-border/60" />
      {show && contain && (
        <img
          src={src}
          alt=""
          aria-hidden="true"
          decoding="async"
          className={`absolute inset-0 w-full h-full object-cover scale-110 blur-2xl opacity-70 ${className}`}
        />
      )}
      {show && (
        <img
          src={src}
          alt=""
          loading={contain ? "eager" : "lazy"}
          decoding="async"
          onError={() => setBroken(true)}
          className={`absolute inset-0 w-full h-full ${contain ? "object-contain" : "object-cover"} ${className}`}
        />
      )}
    </>
  );
}
