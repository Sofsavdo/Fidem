import React, { useEffect } from "react";
import { useApp } from "@/contexts/AppContext";
import { Megaphone } from "lucide-react";
import { photoSrc } from "@/lib/photo";
import { useAnnouncements } from "@/hooks/queries";
import { EmptyState } from "@/components/kit";

// Anonslar — the platform news feed: photo posts, releases, and (later)
// match/wedding success stories.
export default function Announcements() {
  const { t } = useApp();
  const { data: items = [], isLoading } = useAnnouncements();

  // Mark the feed as seen so the bottom-nav dot clears.
  useEffect(() => {
    const latest = items[0]?.created_at;
    if (latest) {
      try { localStorage.setItem("fidem_anons_seen", latest); } catch { /* ignore */ }
    }
  }, [items]);

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
              <img
                loading="lazy"
                decoding="async"
                src={photoSrc(a.image_url)}
                alt=""
                className="w-full max-h-72 object-cover"
              />
            )}
            <div className="p-4">
              <h2 className="font-heading text-lg font-semibold leading-snug">{a.title}</h2>
              {a.text && <p className="text-sm text-muted-foreground mt-1.5 leading-relaxed whitespace-pre-line">{a.text}</p>}
              <p className="text-[11px] text-muted-foreground mt-2.5">
                {a.created_at ? new Date(a.created_at).toLocaleDateString() : ""}
              </p>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
