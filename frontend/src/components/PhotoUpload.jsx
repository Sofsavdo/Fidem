import React, { useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
import { Upload, Loader2 } from "lucide-react";
import { photoSrc } from "@/lib/photo";

export default function PhotoUpload({ value, onChange, testid = "photo-upload" }) {
  const [uploading, setUploading] = useState(false);

  const onFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await api.post("/files/upload", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      // Store absolute path; viewer's JWT appended when rendering
      const base = process.env.REACT_APP_BACKEND_URL;
      const absUrl = `${base}${r.data.url}`;
      onChange(absUrl);
      toast.success("Yuklandi");
    } catch (e) {
      toast.error("Yuklash xatosi");
    } finally {
      setUploading(false);
    }
  };

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
          accept="image/jpeg,image/png,image/webp,image/gif"
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
