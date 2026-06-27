import React, { useEffect, useRef, useState } from "react";

/**
 * Wheel picker — iOS-style scroll list. One column.
 * Pure CSS scroll-snap; no external lib.
 */
export function WheelColumn({ items, value, onChange, formatter, dataTestId }) {
  const ref = useRef(null);
  const itemH = 36; // px row height
  const visible = 5; // rows visible
  const padH = ((visible - 1) / 2) * itemH;

  useEffect(() => {
    const idx = items.indexOf(value);
    if (idx >= 0 && ref.current) {
      ref.current.scrollTo({ top: idx * itemH, behavior: "auto" });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items, value]);

  const onScroll = () => {
    if (!ref.current) return;
    clearTimeout(ref.current._t);
    ref.current._t = setTimeout(() => {
      const idx = Math.round(ref.current.scrollTop / itemH);
      const clamped = Math.max(0, Math.min(items.length - 1, idx));
      const newVal = items[clamped];
      if (newVal !== undefined && newVal !== value) onChange(newVal);
      ref.current.scrollTo({ top: clamped * itemH, behavior: "smooth" });
    }, 80);
  };

  return (
    <div className="relative flex-1" style={{ height: visible * itemH }}>
      <div
        ref={ref}
        data-testid={dataTestId}
        onScroll={onScroll}
        className="h-full overflow-y-auto no-scrollbar"
        style={{ scrollSnapType: "y mandatory", WebkitOverflowScrolling: "touch" }}
      >
        <div style={{ paddingTop: padH, paddingBottom: padH }}>
          {items.map((it) => (
            <div
              key={it}
              onClick={() => onChange(it)}
              className={`grid place-items-center text-center text-sm transition ${
                it === value ? "font-semibold text-foreground scale-110" : "text-muted-foreground"
              }`}
              style={{ height: itemH, scrollSnapAlign: "center" }}
            >
              {formatter ? formatter(it) : it}
            </div>
          ))}
        </div>
      </div>
      {/* Center selection band */}
      <div className="absolute left-0 right-0 pointer-events-none border-y-2 border-primary/30 bg-primary/5" style={{ top: padH, height: itemH }} />
      {/* Fade top/bottom */}
      <div className="absolute top-0 inset-x-0 h-12 pointer-events-none bg-gradient-to-b from-card to-transparent" />
      <div className="absolute bottom-0 inset-x-0 h-12 pointer-events-none bg-gradient-to-t from-card to-transparent" />
    </div>
  );
}

export default function WheelDatePicker({ value, onChange, minAge = 18, maxAge = 80 }) {
  // value: "YYYY-MM-DD"
  const today = new Date();
  const maxYear = today.getFullYear() - minAge;
  const minYear = today.getFullYear() - maxAge;
  const years = [];
  for (let y = maxYear; y >= minYear; y--) years.push(y);
  const months = Array.from({ length: 12 }, (_, i) => i + 1);

  const parse = (v) => {
    const [y, m, d] = (v || `${maxYear - 7}-01-01`).split("-").map(Number);
    return { y: y || maxYear - 7, m: m || 1, d: d || 1 };
  };
  const [{ y, m, d }, setVal] = useState(parse(value));

  const daysInMonth = (yy, mm) => new Date(yy, mm, 0).getDate();
  const days = Array.from({ length: daysInMonth(y, m) }, (_, i) => i + 1);

  const update = (patch) => {
    const nv = { y, m, d, ...patch };
    nv.d = Math.min(nv.d, daysInMonth(nv.y, nv.m));
    setVal(nv);
    const iso = `${nv.y}-${String(nv.m).padStart(2, "0")}-${String(nv.d).padStart(2, "0")}`;
    onChange(iso);
  };

  const monthNames = ["Yan", "Fev", "Mar", "Apr", "May", "Iyun", "Iyul", "Avg", "Sen", "Okt", "Noy", "Dek"];

  return (
    <div className="rounded-2xl border border-border bg-card overflow-hidden" data-testid="wheel-date-picker">
      <div className="flex bg-card">
        <WheelColumn items={days} value={d} onChange={(v) => update({ d: v })} dataTestId="wheel-day" />
        <WheelColumn items={months} value={m} onChange={(v) => update({ m: v })} formatter={(mm) => monthNames[mm - 1]} dataTestId="wheel-month" />
        <WheelColumn items={years} value={y} onChange={(v) => update({ y: v })} dataTestId="wheel-year" />
      </div>
      <div className="text-center py-2 text-xs text-muted-foreground border-t border-border/40">
        {d} {monthNames[m - 1]} {y} — Yosh: {today.getFullYear() - y}
      </div>
    </div>
  );
}
