// Contact exchange: the only way to move a conversation off FIDEM. Both
// people must pass the selfie check, write 10+ messages each, and the other
// person must agree. Contacts typed into a message are blocked.
import React from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Check, X, ShieldCheck } from "lucide-react";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { purchasePlan } from "@/lib/purchase";

export function useContactExchange(otherId) {
  const [state, setState] = React.useState(null);
  const last = React.useRef(0);
  const load = React.useCallback(async (force = false) => {
    if (!otherId) return;
    if (!force && Date.now() - last.current < 15000) return;
    last.current = Date.now();
    try {
      const r = await api.get(`/chat/contact-exchange/${otherId}`);
      setState(r.data);
    } catch { /* not critical */ }
  }, [otherId]);
  React.useEffect(() => { load(true); }, [load]);
  return { state, reload: load };
}

const ERR = {
  selfie_required: "cx_err_selfie",
  other_not_verified: "cx_err_other_selfie",
  premium_required: "cx_err_premium",
  add_contact_first: "cx_err_add_contact",
  need_more_messages: "cx_err_messages",
  blocked: "msg_blocked_error",
};

function Req({ ok, children }) {
  return (
    <li className={`flex items-center gap-1.5 ${ok ? "text-emerald-700 dark:text-emerald-400" : "text-muted-foreground"}`}>
      {ok ? <Check className="w-3.5 h-3.5 shrink-0" /> : <span className="w-3.5 h-3.5 shrink-0 rounded-full border border-current" />}
      <span className="min-w-0">{children}</span>
    </li>
  );
}

export function IncomingExchange({ state, otherId, otherName, onAnswered }) {
  const { t } = useApp();
  const [busy, setBusy] = React.useState(false);
  if (!state || state.status !== "pending" || state.direction !== "incoming") return null;
  const answer = async (accept) => {
    setBusy(true);
    try {
      await api.post(`/chat/contact-exchange/${otherId}/respond`, { accept });
      toast.success(t(accept ? "cx_accepted_toast" : "cx_declined_toast"));
    } catch (e) {
      const d = (e?.response?.data?.detail || "").toString();
      toast.error(t(ERR[d] || "error_generic"));
    } finally {
      setBusy(false);
      onAnswered?.();
    }
  };
  return (
    <div data-testid="cx-incoming" className="rounded-2xl border border-secondary/40 bg-secondary/10 px-3 py-2 space-y-2">
      <p className="text-xs">📇 {t("cx_incoming").replace("{name}", otherName || "")}</p>
      <div className="flex gap-2">
        <button data-testid="cx-accept" disabled={busy} onClick={() => answer(true)} className="flex-1 rounded-full bg-primary text-white text-xs font-semibold py-1.5 disabled:opacity-50">{t("cx_accept")}</button>
        <button data-testid="cx-decline" disabled={busy} onClick={() => answer(false)} className="flex-1 rounded-full border border-border text-xs font-semibold py-1.5 disabled:opacity-50">{t("cx_decline")}</button>
      </div>
    </div>
  );
}

export function AcceptedContacts({ state }) {
  const { t } = useApp();
  if (!state || state.status !== "accepted" || !state.contacts) return null;
  const { telegram, phone } = state.contacts;
  return (
    <div data-testid="cx-contacts" className="rounded-2xl border border-emerald-300 bg-emerald-50 dark:bg-emerald-950/30 dark:border-emerald-800 px-3 py-2 text-xs flex flex-wrap items-center gap-x-3 gap-y-1">
      <span className="font-medium">✅ {t("cx_contacts_title")}</span>
      {telegram && <a className="text-primary underline" href={`https://t.me/${telegram}`} target="_blank" rel="noreferrer">@{telegram}</a>}
      {phone && <a className="text-primary underline" href={`tel:${phone}`}>{phone}</a>}
    </div>
  );
}

export function ExchangePanel({ state, otherId, onClose, onChanged }) {
  const { t } = useApp();
  const [busy, setBusy] = React.useState(false);
  if (!state) return null;
  const need = state.need_messages || 10;
  const enoughMine = state.my_messages >= need;
  const enoughTheirs = state.their_messages >= need;
  const ready = state.me_verified && state.other_verified && state.me_premium && state.me_has_contacts && enoughMine && enoughTheirs;
  const request = async () => {
    setBusy(true);
    try {
      await api.post(`/chat/contact-exchange/${otherId}`);
      toast.success(t("cx_sent_toast"));
      onChanged?.();
    } catch (e) {
      const d = (e?.response?.data?.detail || "").toString();
      if (d === "premium_required") purchasePlan("premium", { source: "contact_exchange", reason: t("cx_err_premium"), onPaid: onChanged });
      else toast.error(t(ERR[d] || "error_generic"));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div data-testid="cx-panel" className="rounded-2xl bg-card border border-border px-3 py-2.5 space-y-2">
      <div className="flex items-start gap-2">
        <ShieldCheck className="w-4 h-4 text-secondary shrink-0 mt-0.5" />
        <p className="text-xs flex-1">{t("cx_title")}</p>
        <button onClick={onClose} className="shrink-0 p-1 rounded-full hover:bg-muted" aria-label={t("pay_close")}><X className="w-3.5 h-3.5" /></button>
      </div>
      {state.status === "accepted" ? (
        <AcceptedContacts state={state} />
      ) : state.status === "pending" && state.direction === "outgoing" ? (
        <p data-testid="cx-waiting" className="text-xs text-muted-foreground">⏳ {t("cx_waiting")}</p>
      ) : state.status === "pending" ? null : (
        <>
          <ul className="space-y-1 text-[11px]">
            <Req ok={state.me_verified}>{state.me_verified ? t("cx_req_me_selfie") : <Link to="/verification" className="underline">{t("cx_req_me_selfie")}</Link>}</Req>
            <Req ok={state.other_verified}>{t("cx_req_other_selfie")}</Req>
            <Req ok={enoughMine && enoughTheirs}>{t("cx_req_messages").replace("{need}", need).replace("{mine}", Math.min(state.my_messages, need)).replace("{theirs}", Math.min(state.their_messages, need))}</Req>
            <Req ok={state.me_has_contacts}>{state.me_has_contacts ? t("cx_req_contacts") : <Link to="/me/settings" className="underline">{t("cx_req_contacts")}</Link>}</Req>
            <Req ok={state.me_premium}>{state.me_premium ? t("cx_req_premium") : <button className="underline" onClick={() => purchasePlan("premium", { source: "contact_exchange", reason: t("cx_err_premium"), onPaid: onChanged })}>{t("cx_req_premium")}</button>}</Req>
          </ul>
          <button data-testid="cx-request" disabled={!ready || busy} onClick={request} className="w-full rounded-full bg-primary text-white text-xs font-semibold py-2 disabled:opacity-40">
            {busy ? "..." : t("cx_request")}
          </button>
        </>
      )}
    </div>
  );
}
