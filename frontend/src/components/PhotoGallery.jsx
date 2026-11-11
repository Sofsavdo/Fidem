import React, { useRef, useState } from "react";
import { toast } from "sonner";
import { Plus, X, Loader2, Star } from "lucide-react";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { photoSrc } from "@/lib/photo";
import { uploadImage } from "@/components/PhotoUpload";

const MAX_EXTRA = 5; // besides the main photo (mirrors backend MAX_EXTRA_PHOTOS)

// "My photos": the main photo plus up to 5 more. The main photo is the one
// shown on cards; the rest are swiped through on the profile.
export default function PhotoGallery() {
  const { t, user, refresh } = useApp();
  const [busy, setBusy] = useState(false);
  const inputRef = useRef(null);
  const extras = user.photos || [];

  const save = async (body) => {
    setBusy(true);
    try {
      await api.patch("/profile", body);
      await refresh();
    } catch (e) {
      console.error("Gallery save error:", e);
      toast.error(t("error_generic"));
    } finally {
      setBusy(false);
    }
  };

  const onPick = async (e) => {
    const files = Array.from(e.target.files || []).slice(0, MAX_EXTRA - extras.length);
    e.target.value = "";
    if (!files.length) return;
    setBusy(true);
    try {
      const urls = [];
      for (const f of files) urls.push(await uploadImage(f));
      await api.patch("/profile", { photos: [...extras, ...urls] });
      await refresh();
    } catch (err) {
      console.error("Gallery upload error:", err);
      toast.error(err?.code === "too_large" ? "Rasm juda katta (max 8MB)" : t("error_generic"));
    } finally {
      setBusy(false);
    }
  };

  const remove = (url) => save({ photos: extras.filter((x) => x !== url) });
  // Promote an extra photo to main; the old main moves into the gallery.
  const makeMain = (url) => save({ photo_url: url, photos: [user.photo_url, ...extras.filter((x) => x !== url)].filter(Boolean) });

  return (
    <div className="rounded-3xl bg-card border border-border p-4 shadow-soft" data-testid="photo-gallery">
      <p className="font-heading text-base font-semibold">{t("gallery_title")}</p>
      <p className="text-xs text-muted-foreground mt-0.5 mb-3">{t("gallery_hint").replace("{n}", MAX_EXTRA)}</p>
      <div className="grid grid-cols-4 gap-2">
        {user.photo_url && (
          <div className="relative aspect-[4/5] rounded-2xl overflow-hidden bg-muted" data-testid="gallery-main">
            <img src={photoSrc(user.photo_url)} alt="" className="w-full h-full object-cover" />
            <span title={t("gallery_main")} aria-label={t("gallery_main")} className="absolute left-1.5 top-1.5 w-6 h-6 grid place-items-center rounded-full bg-black/60 text-white">
              <Star className="w-3 h-3" />
            </span>
          </div>
        )}
        {extras.map((url) => (
          <div key={url} className="relative aspect-[4/5] rounded-2xl overflow-hidden bg-muted" data-testid="gallery-item">
            <img src={photoSrc(url)} alt="" loading="lazy" decoding="async" className="w-full h-full object-cover" />
            <button
              type="button"
              disabled={busy}
              onClick={() => remove(url)}
              title={t("gallery_remove")}
              data-testid="gallery-remove"
              className="absolute right-1.5 top-1.5 w-6 h-6 grid place-items-center rounded-full bg-black/60 text-white disabled:opacity-50"
            >
              <X className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => makeMain(url)}
              data-testid="gallery-make-main"
              className="absolute inset-x-1 bottom-1 rounded-full bg-black/60 text-white text-[9px] py-0.5 disabled:opacity-50"
            >
              {t("gallery_make_main")}
            </button>
          </div>
        ))}
        {extras.length < MAX_EXTRA && (
          <label
            className={`aspect-[4/5] rounded-2xl border-2 border-dashed border-border grid place-items-center text-muted-foreground cursor-pointer hover:bg-muted/60 ${busy ? "opacity-60 pointer-events-none" : ""}`}
            data-testid="gallery-add"
            title={t("gallery_add")}
          >
            <input ref={inputRef} type="file" accept="image/*" multiple onChange={onPick} className="hidden" data-testid="gallery-input" />
            {busy ? <Loader2 className="w-5 h-5 animate-spin" /> : <Plus className="w-6 h-6" />}
          </label>
        )}
      </div>
    </div>
  );
}
