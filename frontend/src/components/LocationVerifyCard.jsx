import React, { useState } from "react";
import { MapPin, Check, Loader2 } from "lucide-react";
import { useApp } from "@/contexts/AppContext";
import { useVerifyLocation } from "@/hooks/queries";
import { toast } from "sonner";

// Map M1: lets a user confirm their city via one GPS read. The coordinate
// is sent once and stored server-side only; the UI never sees or keeps it.
export default function LocationVerifyCard() {
  const { t, user, refresh } = useApp();
  const verify = useVerifyLocation();
  const [busy, setBusy] = useState(false);

  if (!user) return null;

  if (user.location_verified) {
    return (
      <div className="rounded-3xl bg-secondary/10 border border-secondary/30 p-4 flex items-center gap-3" data-testid="location-verified-card">
        <Check className="w-5 h-5 text-secondary shrink-0" />
        <p className="text-sm font-medium text-secondary">{t("location_verified_ok")}</p>
      </div>
    );
  }

  const start = () => {
    if (!navigator.geolocation) {
      toast.error(t("location_verify_unavailable"));
      return;
    }
    setBusy(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const r = await verify.mutateAsync({ lat: pos.coords.latitude, lng: pos.coords.longitude });
          if (r.verified) {
            toast.success(t("location_verified_ok"));
            await refresh();
          } else if (r.mismatch && r.detected_region) {
            toast.error(t("location_verify_mismatch").replace("{region}", r.detected_region));
          } else {
            toast.error(t("location_verify_unavailable"));
          }
        } catch {
          toast.error(t("location_verify_unavailable"));
        } finally {
          setBusy(false);
        }
      },
      () => {
        toast.error(t("location_verify_denied"));
        setBusy(false);
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 }
    );
  };

  return (
    <div className="rounded-3xl bg-gradient-to-r from-secondary/8 to-card border border-secondary/25 p-4" data-testid="location-verify-card">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-2xl bg-secondary/12 grid place-items-center shrink-0">
          <MapPin className="w-5 h-5 text-secondary" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="font-heading text-base font-semibold">{t("location_verify_title")}</p>
          <p className="text-xs text-muted-foreground mt-0.5">{t("location_verify_desc")}</p>
          <button
            data-testid="location-verify-btn"
            onClick={start}
            disabled={busy}
            className="btn-primary mt-3 inline-flex"
            style={{ width: "auto" }}
          >
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <MapPin className="w-4 h-4" />}
            {t("location_verify_btn")}
          </button>
        </div>
      </div>
    </div>
  );
}
