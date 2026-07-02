import React, { useEffect, useMemo, useState } from "react";
import { Check, ChevronDown, Search, X } from "lucide-react";
import { getRegionsFor } from "@/lib/locations";

/**
 * RegionSelect — closed-by-default searchable region picker.
 * - If selected country has a known regions list → dropdown.
 * - If not → simple free-text input.
 * Props:
 *   country: string  (canonical English country name, e.g. "Uzbekistan")
 *   value: string
 *   onChange: (region: string) => void
 *   placeholder, testid
 */
export default function RegionSelect({ country, value, onChange, placeholder = "Select region", testid = "region-select" }) {
  const regions = useMemo(() => getRegionsFor(country), [country]);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  // When country changes, clear region if it doesn't belong to the new country.
  useEffect(() => {
    if (regions && value && !regions.includes(value)) {
      onChange("");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [country]);

  const filtered = useMemo(() => {
    if (!regions) return [];
    const q = query.trim().toLowerCase();
    if (!q) return regions;
    return regions.filter((r) => r.toLowerCase().includes(q));
  }, [regions, query]);

  // Free-text fallback for countries without a regions list
  if (!regions) {
    return (
      <input
        data-testid={testid}
        className="input"
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
    );
  }

  const close = () => {
    setOpen(false);
    setQuery("");
  };
  const pick = (r) => {
    close();
    onChange(r);
  };

  return (
    <div className="relative">
      <button
        type="button"
        data-testid={testid}
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="input flex items-center justify-between w-full text-left"
      >
        <span className="truncate">{value || <span className="text-muted-foreground">{placeholder}</span>}</span>
        <ChevronDown className={`w-4 h-4 shrink-0 text-muted-foreground transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={close} />
          <div className="absolute z-50 mt-2 left-0 right-0 rounded-2xl border border-border bg-card shadow-xl overflow-hidden" data-testid={`${testid}-panel`}>
            <div className="flex items-center gap-2 px-3 py-2 border-b border-border bg-muted/40">
              <Search className="w-4 h-4 text-muted-foreground shrink-0" />
              <input
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={placeholder}
                className="flex-1 bg-transparent outline-none text-sm placeholder:text-muted-foreground"
                data-testid={`${testid}-search`}
              />
              {query && (
                <button type="button" onClick={() => setQuery("")} className="text-muted-foreground hover:text-foreground" aria-label="Clear">
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
            <div className="max-h-72 overflow-y-auto overscroll-contain">
              {filtered.length === 0 && (
                <div className="px-4 py-6 text-center text-sm text-muted-foreground">No regions found</div>
              )}
              {filtered.map((r) => {
                const active = value === r;
                return (
                  <button
                    key={r}
                    type="button"
                    onClick={() => pick(r)}
                    data-testid={`${testid}-opt-${r}`}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm text-left hover:bg-muted transition ${active ? "bg-primary/10" : ""}`}
                  >
                    <span className="flex-1 truncate">{r}</span>
                    {active && <Check className="w-4 h-4 text-foreground" />}
                  </button>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
