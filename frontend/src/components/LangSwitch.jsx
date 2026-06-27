import React from "react";
import { useApp } from "@/contexts/AppContext";

const LANGS = ["uz", "ru", "en"];

// Compact segmented language switcher (UZ | RU | EN) used on Landing & Auth.
export default function LangSwitch({ className = "" }) {
  const { lang, setLang } = useApp();
  return (
    <div
      data-testid="lang-switch"
      className={`inline-flex items-center rounded-full bg-muted/80 border border-border/60 p-0.5 ${className}`}
    >
      {LANGS.map((l) => (
        <button
          key={l}
          type="button"
          data-testid={`lang-${l}`}
          onClick={() => setLang(l)}
          className={`px-2.5 py-1 text-xs font-semibold uppercase rounded-full transition-colors ${
            lang === l
              ? "bg-primary text-white shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          {l}
        </button>
      ))}
    </div>
  );
}
