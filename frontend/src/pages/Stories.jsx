import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { Heart, Eye, Star } from "lucide-react";
import { Link } from "react-router-dom";

export default function Stories() {
  const [stories, setStories] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/stories?limit=50").then((r) => { setStories(r.data || []); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  return (
    <div className="p-5 max-w-5xl mx-auto pb-24" data-testid="stories-page">
      <div className="flex items-start gap-3 mb-6">
        <div className="w-12 h-12 rounded-2xl bg-primary/10 text-primary grid place-items-center">
          <Heart className="w-5 h-5" fill="currentColor" />
        </div>
        <div>
          <h1 className="font-heading text-2xl font-semibold">Muvaffaqiyat hikoyalari</h1>
          <p className="text-sm text-muted-foreground">FIDEM orqali nikohlangan oilalar o'z hikoyalarini ulashadi</p>
        </div>
      </div>

      {loading && <p className="text-center text-muted-foreground py-12">Yuklanmoqda…</p>}
      {!loading && stories.length === 0 && (
        <div className="rounded-3xl bg-card border border-border p-8 text-center">
          <p className="text-muted-foreground">Hozircha hikoyalar yo'q. Birinchi siz bo'ling!</p>
          <Link to="/stories/submit" className="mt-4 inline-block rounded-xl bg-primary text-white px-4 py-2 text-sm font-medium">Hikoyamni yuborish</Link>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-4">
        {stories.map((s) => (
          <article key={s.id} data-testid={`story-${s.id}`} className="rounded-3xl bg-card border border-border overflow-hidden hover:shadow-elevated transition">
            {s.photo_url && (
              <div className="aspect-[16/10] bg-muted overflow-hidden relative">
                <img src={s.photo_url} alt={s.couple_names} className="w-full h-full object-cover" />
                {s.featured && (
                  <span className="absolute top-3 right-3 inline-flex items-center gap-1 rounded-full bg-gold text-ink text-[10px] font-medium px-2 py-1">
                    <Star className="w-3 h-3" fill="currentColor" /> Tanlangan
                  </span>
                )}
              </div>
            )}
            <div className="p-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-heading text-lg font-semibold">{s.couple_names}</h3>
                <span className="text-xs text-muted-foreground">{s.year}</span>
              </div>
              <p className="text-xs text-muted-foreground mb-2">{s.region}</p>
              <p className="text-sm leading-relaxed text-foreground/90 line-clamp-5">{s.story_text}</p>
              <div className="mt-3 pt-3 border-t border-border/60 flex items-center justify-between">
                <span className="text-xs text-muted-foreground inline-flex items-center gap-1"><Eye className="w-3 h-3" /> {s.views || 0}</span>
                <span className="text-[10px] uppercase tracking-wider text-primary">FIDEM nikoh hikoyasi</span>
              </div>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
