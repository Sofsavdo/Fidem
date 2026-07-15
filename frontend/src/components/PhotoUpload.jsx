import React, { useState } from "react";
import api, { API } from "@/lib/api";
import { toast } from "sonner";
import { Upload, Loader2, Camera } from "lucide-react";
import { photoSrc } from "@/lib/photo";

// Phone camera photos are routinely 4-12MB; the backend caps uploads at 8MB
// and Uzbek mobile networks make even a 5MB upload feel broken. Since the
// photo is the MANDATORY last onboarding step, a failed/slow upload here was
// silently killing signups — so every image is downscaled client-side first
// (max 1280px, JPEG q0.82 → typically 150-400KB, uploads in ~1s).
async function compressImage(file, maxDim = 1280, quality = 0.82) {
  if (!/^image\//.test(file.type || "")) return file;
  try {
    let bitmap;
    if (typeof createImageBitmap === "function") {
      bitmap = await createImageBitmap(file);
    } else {
      bitmap = await new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = reject;
        img.src = URL.createObjectURL(file);
      });
    }
    const w0 = bitmap.width || bitmap.naturalWidth;
    const h0 = bitmap.height || bitmap.naturalHeight;
    if (!w0 || !h0) return file;
    const scale = Math.min(1, maxDim / Math.max(w0, h0));
    const w = Math.max(1, Math.round(w0 * scale));
    const h = Math.max(1, Math.round(h0 * scale));
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    canvas.getContext("2d").drawImage(bitmap, 0, 0, w, h);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", quality));
    if (blob && blob.size > 0 && blob.size < file.size) {
      const name = (file.name || "photo").replace(/\.\w+$/, "") + ".jpg";
      return new File([blob], name, { type: "image/jpeg" });
    }
  } catch { /* fall through to the original file */ }
  return file;
}

export default function PhotoUpload({ value, onChange, testid = "photo-upload", avatar = false, name = "" }) {
  const [uploading, setUploading] = useState(false);

  const onFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const compressed = await compressImage(file);
      if (compressed.size > 8 * 1024 * 1024) {
        toast.error("Rasm juda katta (max 8MB) — boshqa rasm tanlang");
        return;
      }
      const fd = new FormData();
      fd.append("file", compressed);
      const r = await api.post("/files/upload", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      // Absolute path; viewer's JWT appended when rendering. API always has a
      // valid base (env or fallback) — raw REACT_APP_BACKEND_URL could be
      // undefined in a misconfigured build and produced "undefined/api/..."
      const base = API.replace(/\/api$/, "");
      onChange(`${base}${r.data.url}`);
      toast.success("Yuklandi");
    } catch (err) {
      const status = err?.response?.status;
      if (status === 413) toast.error("Rasm juda katta (max 8MB) — boshqa rasm tanlang");
      else if (status === 400) toast.error("Bu fayl turi qabul qilinmaydi — jpg/png yuklang");
      else toast.error("Yuklash xatosi — internetni tekshirib qayta urining");
    } finally {
      setUploading(false);
    }
  };

  // Compact avatar mode: a single tappable photo with a camera badge — used on
  // the profile card so the photo lives in exactly one place.
  if (avatar) {
    return (
      <label className="relative w-16 h-16 rounded-2xl overflow-hidden bg-muted grid place-items-center cursor-pointer flex-shrink-0" data-testid={`${testid}-avatar`}>
        <input type="file" accept="image/*" onChange={onFile} className="hidden" data-testid={testid} />
        {value ? (
          <img loading="lazy" decoding="async" src={photoSrc(value)} alt="" className="w-full h-full object-cover" />
        ) : (
          <span className="text-muted-foreground text-xl font-heading">{name?.[0] || "?"}</span>
        )}
        <span className="absolute bottom-0 inset-x-0 bg-black/55 text-white h-5 grid place-items-center">
          {uploading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Camera className="w-3 h-3" />}
        </span>
      </label>
    );
  }

  return (
    <div className="flex items-center gap-3">
      {value ? (
        <img loading="lazy" decoding="async" src={photoSrc(value)} alt="" className="w-20 h-20 rounded-2xl object-cover border border-border" data-testid={`${testid}-preview`} />
      ) : (
        <div className="w-20 h-20 rounded-2xl bg-muted grid place-items-center text-muted-foreground">
          <Upload className="w-5 h-5" />
        </div>
      )}
      <label className="flex-1">
        <input
          data-testid={testid}
          type="file"
          accept="image/*"
          onChange={onFile}
          className="hidden"
        />
        <span className="inline-flex items-center gap-2 rounded-2xl border border-border bg-card px-4 py-2.5 cursor-pointer hover:bg-muted text-sm">
          {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
          {uploading ? "..." : value ? "O'zgartirish" : "Yuklash"}
        </span>
      </label>
    </div>
  );
}
