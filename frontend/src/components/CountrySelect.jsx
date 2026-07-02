import React, { useMemo, useState } from "react";
import { Check, ChevronDown, Search, X } from "lucide-react";
import { COUNTRIES, findCountry, countryLabel } from "@/lib/locations";

/**
 * CountrySelect — closed-by-default searchable dropdown for ~80 countries.
 * Props:
 *   value: string  (canonical English country name, e.g. "Uzbekistan")
 *   onChange: (name: string) => void
 *   lang: "uz" | "ru" | "en"
 *   placeholder, testid
 */
export default function CountrySelect({ value, onChange, lang = "en", placeholder = "Select country", testid = "country-select" }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  const selected = useMemo(() => findCountry(value), [value]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return COUNTRIES;
    return COUNTRIES.filter((c) => {
      return (
        c.name.toLowerCase().includes(q) ||
        c.code.toLowerCase().includes(q) ||
        (c.name_uz && c.name_uz.toLowerCase().includes(q)) ||
        (c.name_ru && c.name_ru.toLowerCase().includes(q))
      );
    });
  }, [query]);

  const close = () => {
    setOpen(false);
    setQuery("");
  };

  const pick = (c) => {
    close();
    onChange(c.name); // canonical English name stored in DB
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
        <span className="flex items-center gap-2 truncate">
          {selected ? (
            <>
              <span className="text-base leading-none">{selected.flag}</span>
              <span className="truncate">{countryLabel(selected, lang)}</span>
            </>
          ) : (
            <span className="text-muted-foreground">{placeholder}</span>
          )}
        </span>
        <ChevronDown className={`w-4 h-4 shrink-0 text-muted-foreground transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <>
          {/* backdrop */}
          <div className="fixed inset-0 z-40" onClick={close} />
          {/* panel */}
          <div
            className="absolute z-50 mt-2 left-0 right-0 rounded-2xl border border-border bg-card shadow-xl overflow-hidden"
            data-testid={`${testid}-panel`}
          >
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
                <div className="px-4 py-6 text-center text-sm text-muted-foreground">No countries found</div>
              )}
              {filtered.map((c) => {
                const active = selected?.code === c.code;
                return (
                  <button
                    key={c.code}
                    type="button"
                    onClick={() => pick(c)}
                    data-testid={`${testid}-opt-${c.code}`}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm text-left hover:bg-muted transition ${active ? "bg-primary/10" : ""}`}
                  >
                    <span className="text-lg leading-none">{c.flag}</span>
                    <span className="flex-1 truncate">{countryLabel(c, lang)}</span>
                    <span className="text-[10px] text-muted-foreground tracking-wider">{c.code}</span>
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
