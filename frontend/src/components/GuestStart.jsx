// Guest mode, first screen: one question (who are you looking for) and the
// app opens. Everything else is asked only when the person wants to act.
import React, { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { track } from "@/lib/analytics";

export default function GuestStart() {
  const { t, refresh } = useApp();
  const [busy, setBusy] = useState(false);
  const pick = async (search_gender) => {
    setBusy(true);
    try {
      await api.post("/profile/guest", { search_gender });
      track("guest_started", { search_gender });
      await refresh();
    } catch {
      toast.error(t("error_generic"));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6 text-center gap-6 bg-gradient-to-b from-primary/10 to-background" data-testid="guest-start">
      <div className="text-5xl">💖</div>
      <div className="space-y-2">
        <h1 className="font-heading text-2xl font-semibold">{t("guest_start_title")}</h1>
        <p className="text-sm text-muted-foreground max-w-xs mx-auto">{t("guest_start_sub")}</p>
      </div>
      <div className="w-full max-w-xs space-y-3">
        <button data-testid="guest-pick-female" disabled={busy} onClick={() => pick("female")} className="w-full rounded-2xl border-2 border-primary/40 bg-card py-4 text-lg font-semibold active:scale-[0.98] transition disabled:opacity-50">
          👩 {t("guest_look_female")}
        </button>
        <button data-testid="guest-pick-male" disabled={busy} onClick={() => pick("male")} className="w-full rounded-2xl border-2 border-secondary/40 bg-card py-4 text-lg font-semibold active:scale-[0.98] transition disabled:opacity-50">
          👨 {t("guest_look_male")}
        </button>
      </div>
      <Link to="/onboarding" className="text-sm text-primary underline">{t("guest_register_now")}</Link>
    </div>
  );
}
