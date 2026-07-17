import React, { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useApp } from "@/contexts/AppContext";
import { ArrowRight, Megaphone } from "lucide-react";
import { photoSrc } from "@/lib/photo";
import { openExternalLink } from "@/lib/telegram";
import api from "@/lib/api";
import { useAnnouncements } from "@/hooks/queries";
import { EmptyState } from "@/components/kit";
import { localeFor } from "@/lib/time";

// Anonslar — the platform news feed: photo posts, releases, and (later)
// match/wedding success stories.
export default function Announcements() {
  const { t, lang } = useApp();
  const navigate = useNavigate();
  const { data: items = [], isLoading } = useAnnouncements();
  const seenRef = useRef(new Set());

  // Mark the feed as seen so the bottom-nav dot clears.
  useEffect(() => {
    const latest = items[0]?.created_at;
    if (latest) {
      try { localStorage.setItem("fidem_anons_seen", latest); } catch { /* ignore */ }
    }
  }, [items]);

  // Unique-viewer tracking for the admin's "necha kishi ko'rdi" count - fire
  // once per post per page load, deduped locally so re-renders don't spam it
  // (the backend upsert is idempotent too, this just saves the round trip).
  useEffect(() => {
    for (const a of items) {
      if (seenRef.current.has(a.id)) continue;
      seenRef.current.add(a.id);
      api.post(`/announcements/${a.id}/view`).catch(() => {});
    }
  }, [items]);

  const openAction = (url) => {
    if (!url) return;
    if (url.startsWith("/")) navigate(url);
    else openExternalLink(url);
  };

  return (
    <div className="px-4 md:px-8 pt-6 pb-8">
      <h1 className="font-heading text-3xl md:text-4xl font-semibold tracking-tight mb-4">{t("anons")}</h1>

      {isLoading && (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="rounded-3xl bg-muted animate-pulse h-40" />
          ))}
        </div>
      )}

      {!isLoading && items.length === 0 && (
        <EmptyState icon={<Megaphone className="w-6 h-6" />} title={t("anons_empty_title")} hint={t("anons_empty_hint")} />
      )}

      <div className="space-y-4 max-w-2xl">
        {items.map((a) => (
          <article key={a.id} className="rounded-3xl bg-card border border-border overflow-hidden" data-testid={`anons-${a.id}`}>
            {a.image_url && (
              /* Fixed aspect box reserves the image's space BEFORE it loads —
                 without it the text painted first and the page jumped when
                 the image arrived. */
              <div className="w-full aspect-[16/9] max-h-72 bg-muted overflow-hidden">
                <img
                  loading="lazy"
                  decoding="async"
                  src={photoSrc(a.image_url)}
                  alt=""
                  className="w-full h-full object-cover"
                />
              </div>
            )}
            <div className="p-4">
              <h2 className="font-heading text-lg font-semibold leading-snug">{a.title}</h2>
              {a.text && <p className="text-sm text-muted-foreground mt-1.5 leading-relaxed whitespace-pre-line">{a.text}</p>}
              {a.action_url && (
                <button
                  type="button"
                  onClick={() => openAction(a.action_url)}
                  className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-primary text-primary-foreground px-4 py-2 text-sm font-medium active:scale-95 transition-transform"
                  data-testid={`anons-action-${a.id}`}
                >
                  {a.action_label || t("anons_learn_more")}
                  <ArrowRight className="w-4 h-4" />
                </button>
              )}
              <p className="text-[11px] text-muted-foreground mt-2.5">
                {a.created_at ? new Date(a.created_at).toLocaleDateString(localeFor(lang)) : ""}
              </p>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
