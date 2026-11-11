import React, { useEffect, useState } from "react";

// Fills its (relatively positioned) parent with a profile photo. While it loads
// - or if it fails - a plain neutral tile stays behind it, and the browser's
// broken-image icon / alt text (which used to print the person's name on top of
// the match badge) never shows.
export default function PhotoFill({ src, className = "" }) {
  const [broken, setBroken] = useState(false);
  useEffect(() => { setBroken(false); }, [src]);
  const show = !!src && !broken;
  return (
    <>
      <div aria-hidden="true" className="absolute inset-0 bg-gradient-to-br from-muted via-muted to-border/60" />
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
