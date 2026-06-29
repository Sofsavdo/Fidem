import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { X, Send } from "lucide-react";
import { toast } from "sonner";
import { useApp } from "@/contexts/AppContext";

export default function RoseModal({ targetId, targetName, onClose, onSent }) {
  const { t } = useApp();
  const [status, setStatus] = useState(null);
  const [note, setNote] = useState("");
  const [sending, setSending] = useState(false);

  useEffect(() => {
    api.get("/roses/status").then((r) => setStatus(r.data));
  }, []);

  const send = async () => {
    setSending(true);
    try {
      await api.post("/roses/send", { to_user_id: targetId, note });
      toast.success(t("rose_sent_to").replace("{name}", targetName));
      onSent && onSent();
      onClose();
    } catch (e) {
      toast.error(t("error_generic"));
    } finally { setSending(false); }
  };

  const buyBundle = async (bundle) => {
    try {
      await api.post("/roses/purchase-balance", { bundle });
      toast.success(t("rose_added"));
      const r = await api.get("/roses/status");
      setStatus(r.data);
    } catch (e) {
      toast.error(t("rose_topup_hint"));
    }
  };

  if (!status) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 grid place-items-center p-4" data-testid="rose-modal">
      <div className="bg-card rounded-3xl max-w-md w-full p-5 relative shadow-elevated">
        <button onClick={onClose} className="absolute top-3 right-3 p-2 rounded-full hover:bg-muted">
          <X className="w-4 h-4" />
        </button>
        <div className="text-center">
          <div className="text-5xl mb-2">🌹</div>
          <h2 className="font-heading text-xl font-semibold">{t("rose_send_title")}</h2>
          <p className="text-sm text-muted-foreground">{t("rose_send_subtitle").replace("{name}", targetName)}</p>
        </div>
        <div className="my-4 rounded-2xl bg-secondary/5 border border-secondary/30 p-3 text-sm">
          <p>{t("rose_available").replace("{total}", status.total).replace("{free}", status.free).replace("{paid}", status.paid)}</p>
          <p className="text-xs text-muted-foreground mt-1">{t("rose_weekly_quota").replace("{quota}", status.weekly_quota)}</p>
        </div>

        <textarea
          data-testid="rose-note"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder={t("rose_note_placeholder")}
          rows={2}
          className="w-full rounded-2xl border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
        />

        <button
          data-testid="rose-send-btn"
          onClick={send}
          disabled={status.total === 0 || sending}
          className="mt-3 w-full rounded-2xl bg-primary text-white py-3 font-medium disabled:opacity-50 inline-flex items-center justify-center gap-2"
        >
          <Send className="w-4 h-4" /> {sending ? t("rose_sending") : t("send")}
        </button>

        {status.total === 0 && (
          <div className="mt-4">
            <p className="text-xs text-center text-muted-foreground mb-2">{t("rose_buy_from_balance")}</p>
            <div className="grid grid-cols-3 gap-2">
              {Object.entries(status.bundles).map(([k, b]) => (
                <button key={k} onClick={() => buyBundle(k)} className="rounded-2xl border border-border hover:bg-muted p-3 text-center">
                  <p className="text-xs text-muted-foreground">{b.count} ta</p>
                  <p className="font-medium text-sm">{b.price.toLocaleString()} {t("sum")}</p>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
