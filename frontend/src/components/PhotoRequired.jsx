import React, { useState } from "react";
import { toast } from "sonner";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import PhotoUpload from "@/components/PhotoUpload";

// Shown instead of the app for an onboarded user who has no profile photo.
// A photo is mandatory: nobody browses, likes or writes without one.
export default function PhotoRequired() {
  const { t, refresh } = useApp();
  const [saving, setSaving] = useState(false);

  const save = async (url) => {
    if (!url || saving) return;
    setSaving(true);
    try {
      await api.patch("/profile", { photo_url: url });
      await refresh();
    } catch (e) {
      console.error("Photo save error:", e);
      toast.error(t("error_generic"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div data-testid="photo-required" className="min-h-screen grid place-items-center px-6 bg-background">
      <div className="w-full max-w-sm rounded-3xl bg-card border border-border/60 shadow-soft p-6 text-center space-y-4">
        <h1 className="font-heading text-2xl font-semibold">{t("photo_gate_title")}</h1>
        <p className="text-sm text-muted-foreground leading-relaxed">{t("photo_gate_desc")}</p>
        <div className="flex justify-center">
          <PhotoUpload value="" onChange={save} testid="photo-required-upload" />
        </div>
        <p className="text-xs text-muted-foreground">{t("photo_required_hint")}</p>
      </div>
    </div>
  );
}
