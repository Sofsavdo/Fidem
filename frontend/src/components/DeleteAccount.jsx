import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Trash2, TriangleAlert } from "lucide-react";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";

// Delete my account: lists what goes (and what is forfeited), asks for the
// confirmation word (and the password, when the account has one), then wipes
// this device's session and cached data as well. Used inside Sozlamalar and
// on the public /delete-account page (the link store listings point to).
export default function DeleteAccount({ startOpen = false }) {
  const { t } = useApp();
  const [open, setOpen] = useState(startOpen);
  const [info, setInfo] = useState(null);
  const [word, setWord] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open || info) return;
    api.get("/account/delete-info").then((r) => setInfo(r.data)).catch(() => toast.error(t("error_generic")));
  }, [open, info, t]);

  const blocked = info?.is_admin || (info?.blockers || []).length > 0;
  const ready = info && !blocked && word.trim().toUpperCase() === info.confirm_word && (!info.has_password || password);

  const wipeDevice = () => {
    try {
      Object.keys(localStorage).filter((k) => k.startsWith("fidem")).forEach((k) => localStorage.removeItem(k));
    } catch { /* storage unavailable: nothing to wipe */ }
    window.location.replace("/welcome");
  };

  const submit = async () => {
    if (!ready || busy) return;
    setBusy(true);
    try {
      await api.post("/account/delete", { confirm: word.trim(), password: info.has_password ? password : undefined });
      toast.success(t("acc_delete_done"));
      wipeDevice();
    } catch (e) {
      const d = (e?.response?.data?.detail || "").toString();
      if (d === "wrong_password") toast.error(t("acc_delete_wrong_pw"));
      else if (d === "pending_money") toast.error(t("acc_delete_blocker_money"));
      else if (d === "admin_account") toast.error(t("acc_delete_admin"));
      else toast.error(t("error_generic"));
      setBusy(false);
    }
  };

  if (!open) {
    return (
      <button
        data-testid="acc-delete-open"
        onClick={() => setOpen(true)}
        className="w-full rounded-2xl border border-rose-300/60 text-rose-600 dark:text-rose-400 py-3 text-sm font-medium flex items-center justify-center gap-2"
      >
        <Trash2 className="w-4 h-4" /> {t("acc_delete_title")}
      </button>
    );
  }

  return (
    <div className="rounded-3xl border border-rose-300/60 bg-rose-50/60 dark:bg-rose-950/20 p-4 space-y-3" data-testid="acc-delete">
      <p className="font-heading font-semibold flex items-center gap-2 text-rose-700 dark:text-rose-300">
        <TriangleAlert className="w-4 h-4" /> {t("acc_delete_title")}
      </p>
      <p className="text-sm leading-snug">{t("acc_delete_intro")}</p>
      {info && (info.balance > 0 || info.earnings > 0) && (
        <p className="text-sm leading-snug font-medium" data-testid="acc-delete-forfeit">
          {t("acc_delete_forfeit").replace("{balance}", info.balance.toLocaleString()).replace("{earnings}", info.earnings.toLocaleString())}
        </p>
      )}
      {info?.is_admin && <p className="text-sm text-rose-700" data-testid="acc-delete-admin">{t("acc_delete_admin")}</p>}
      {(info?.blockers || []).length > 0 && <p className="text-sm text-rose-700" data-testid="acc-delete-blocked">{t("acc_delete_blocker_money")}</p>}
      {info && !blocked && (
        <>
          <label className="block text-xs text-muted-foreground">
            {t("acc_delete_type").replace("{word}", info.confirm_word)}
            <input
              data-testid="acc-delete-word"
              value={word}
              onChange={(e) => setWord(e.target.value)}
              autoCapitalize="characters"
              className="input mt-1"
            />
          </label>
          {info.has_password && (
            <label className="block text-xs text-muted-foreground">
              {t("acc_delete_password")}
              <input
                data-testid="acc-delete-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input mt-1"
              />
            </label>
          )}
        </>
      )}
      <div className="flex gap-2">
        <button
          data-testid="acc-delete-confirm"
          onClick={submit}
          disabled={!ready || busy}
          className="flex-1 rounded-2xl bg-rose-600 text-white py-3 text-sm font-semibold disabled:opacity-40"
        >
          {busy ? "…" : t("acc_delete_btn")}
        </button>
        <button onClick={() => { setOpen(false); setWord(""); setPassword(""); }} className="rounded-2xl border border-border px-4 text-sm">
          {t("cancel")}
        </button>
      </div>
    </div>
  );
}
