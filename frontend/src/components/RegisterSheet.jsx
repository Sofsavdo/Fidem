// "Finish registration" sheet: opened by any action a guest tries (like,
// write, open a photo...) and by the API when it answers onboarding_required.
import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { X } from "lucide-react";
import { useApp } from "@/contexts/AppContext";
import { track } from "@/lib/analytics";
import { NEED_REGISTRATION_EVENT, rememberReturnPath } from "@/lib/guest";

export default function RegisterSheet() {
  const [open, setOpen] = useState(null);
  const { t } = useApp();
  const nav = useNavigate();
  const loc = useLocation();

  useEffect(() => {
    const h = (e) => {
      setOpen(e.detail || {});
      track("guest_register_prompt", { reason: e.detail?.reason || "" });
    };
    window.addEventListener(NEED_REGISTRATION_EVENT, h);
    return () => window.removeEventListener(NEED_REGISTRATION_EVENT, h);
  }, []);

  if (!open) return null;
  const go = () => {
    rememberReturnPath(loc.pathname + loc.search);
    setOpen(null);
    track("guest_register_start", { reason: open.reason || "" });
    nav("/onboarding");
  };
  return (
    <div className="fixed inset-0 flex items-end" style={{ zIndex: 10002 }} data-testid="register-sheet">
      <div className="absolute inset-0 bg-black/45" onClick={() => setOpen(null)} />
      <div className="relative w-full max-w-md mx-auto bg-card rounded-t-3xl p-5 space-y-3"
        style={{ paddingBottom: "max(1.25rem, env(safe-area-inset-bottom))" }}>
        <div className="flex items-start justify-between gap-3">
          <h3 className="font-heading text-xl font-semibold">✨ {t("reg_sheet_title")}</h3>
          <button onClick={() => setOpen(null)} className="p-2 rounded-full hover:bg-muted" aria-label={t("pay_close")}><X className="w-4 h-4" /></button>
        </div>
        <p className="text-sm text-muted-foreground leading-relaxed">{t("reg_sheet_desc")}</p>
        <ul className="text-sm space-y-1.5">
          <li>💬 {t("reg_perk_write")}</li>
          <li>❤️ {t("reg_perk_like")}</li>
          <li>📸 {t("reg_perk_photos")}</li>
        </ul>
        <button data-testid="register-sheet-go" onClick={go} className="btn-primary">{t("reg_sheet_cta")}</button>
        <button onClick={() => setOpen(null)} className="w-full text-sm text-muted-foreground py-1">{t("reg_sheet_later")}</button>
      </div>
    </div>
  );
}
