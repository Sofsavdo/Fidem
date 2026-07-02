import React, { useEffect, useRef, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import GiftModal from "@/components/GiftModal";
import RoseModal from "@/components/RoseModal";
import ChatVoiceRecorder from "@/components/ChatVoiceRecorder";
import { ArrowLeft, Send, Gift, MoreVertical, Ban, Flag, Wand2, Play } from "lucide-react";
import { photoSrc } from "@/lib/photo";
import { formatLastActive } from "@/lib/time";
import { toast } from "sonner";

export default function Chat() {
  const { otherId } = useParams();
  const { user, t } = useApp();
  const nav = useNavigate();
  const [other, setOther] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [showTemplates, setShowTemplates] = useState(true);
  const [access, setAccess] = useState(null);
  const [unlocking, setUnlocking] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [giftOpen, setGiftOpen] = useState(false);
  const [roseOpen, setRoseOpen] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);
  const [icebreakers, setIcebreakers] = useState([]);
  const [aiLoading, setAiLoading] = useState(false);
  const endRef = useRef(null);

  const chatId = user && otherId ? [user.id, otherId].sort().join("_") : null;
  const { wsEvent, lang } = useApp();

  useEffect(() => {
    api.get(`/icebreakers?lang=${lang || "uz"}`).then((r) => setIcebreakers(r.data || [])).catch(() => {});
  }, [lang]);

  const load = async () => {
    try {
      const [c, a, m] = await Promise.all([
        api.get(`/candidates/${otherId}`),
        api.get(`/chat/access/${otherId}`).catch(() => ({ data: null })),
        chatId ? api.get(`/messages/${chatId}`).catch(() => ({ data: [] })) : Promise.resolve({ data: [] }),
      ]);
      setOther(c.data);
      setAccess(a.data);
      setMessages(m.data || []);
    } catch (e) { /* ignore */ }
  };

  const refreshAccess = async () => {
    try {
      const a = await api.get(`/chat/access/${otherId}`);
      setAccess(a.data);
    } catch { /* ignore */ }
  };

  const unlockChat = async (method) => {
    setUnlocking(true);
    try {
      if (method === "click") {
        const r = await api.post("/payments/create", { purpose: "chat_unlock", target_user_id: otherId });
        if (r.data?.payment_link) window.open(r.data.payment_link, "_blank");
        toast.info(t("redirecting_payment") || "To'lov sahifasiga o'tilmoqda...");
      } else {
        await api.post("/chat/unlock", { target_id: otherId, method });
        toast.success(t("chat_unlocked") || "Suhbat ochildi ✅");
        await refreshAccess();
      }
    } catch (err) {
      toast.error("Error");
    } finally {
      setUnlocking(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line
  }, [otherId, user]);

  // Real-time: append incoming WS messages that belong to this chat
  useEffect(() => {
    if (!wsEvent || wsEvent.type !== "message" || !chatId) return;
    const m = wsEvent.data;
    if (!m || m.chat_id !== chatId) return;
    setMessages((prev) => {
      if (prev.some((x) => x.id === m.id)) return prev;
      return [...prev, m];
    });
    // mark as read if I am the recipient
    if (m.to_user_id === user?.id) {
      api.get(`/messages/${chatId}`).catch(() => {}); // server-side mark-read happens on GET
    }
    // eslint-disable-next-line
  }, [wsEvent, chatId, user]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  const send = async (txt, isSuper = false) => {
    const finalText = txt ?? text;
    if (!finalText.trim()) return;
    setSending(true);
    try {
      await api.post("/messages/send", { to_user_id: otherId, text: finalText, is_super: isSuper });
      setText("");
      setShowTemplates(false);
      // Optimistic: don't reload, let WebSocket handle the update
    } catch (e) {
      toast.error(t("error"));
      load(); // Reload only on error
    } finally { setSending(false); }
  };

  const sendVoice = async ({ voice_url, voice_duration }) => {
    setSending(true);
    try {
      await api.post("/messages/send", {
        to_user_id: otherId,
        text: "",
        kind: "voice",
        voice_url,
        voice_duration,
      });
      setShowTemplates(false);
      toast.success("✅");
      // Optimistic: don't reload, let WebSocket handle the update
    } catch (e) {
      toast.error(t("error"));
      load(); // Reload only on error
    } finally { setSending(false); }
  };

  const sendGift = (kind) => {
    setGiftOpen(true);
    // legacy quick-send kept for backward compat — not used now
  };

  const genAiIcebreakers = async () => {
    setAiLoading(true);
    try {
      const r = await api.get(`/ai/icebreakers/${otherId}?lang=${lang || "uz"}`);
      setIcebreakers(r.data.questions || []);
      toast.success("🤖 AI ✅");
    } catch (e) {
      toast.error(t("error"));
    } finally { setAiLoading(false); }
  };

  const blockUser = async () => {
    try {
      await api.post("/messages/block", { user_id: otherId });
      toast.success(t("block"));
      setMenuOpen(false);
      nav("/messages");
    } catch (e) { toast.error(t("error")); }
  };
  const reportUser = async (reason) => {
    if (!reason) return;
    try {
      await api.post("/messages/report", { user_id: otherId, reason });
      toast.success(t("reported"));
      setReportOpen(false);
      setMenuOpen(false);
    } catch (e) { toast.error(t("error")); }
  };

  if (!other) {
    return (
      <div className="flex flex-col min-h-screen pb-32">
        <div className="sticky top-0 z-30 glass border-b border-border/60 px-4 py-3 flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-muted animate-pulse" />
          <div className="flex-1">
            <div className="h-5 bg-muted rounded animate-pulse w-1/3 mb-2" />
            <div className="h-4 bg-muted rounded animate-pulse w-1/4" />
          </div>
        </div>
        <div className="flex-1 px-4 py-4 space-y-2">
          {[...Array(5)].map((_, i) => (
            <div key={i} className={`max-w-[75%] rounded-2xl px-3.5 py-2 h-12 ${i % 2 === 0 ? "ml-auto bg-muted animate-pulse" : "bg-muted animate-pulse"}`} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen pb-32">
      <div className="sticky top-0 z-30 glass border-b border-border/60 px-4 py-3 flex items-center gap-3" style={{ paddingTop: "max(12px, env(safe-area-inset-top))" }}>
        <Link to="/messages" className="p-2 rounded-full hover:bg-muted" data-testid="chat-back">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <Link to={`/candidate/${other.id}`} className="flex items-center gap-3 flex-1 min-w-0">
          <div className="w-10 h-10 rounded-full overflow-hidden bg-muted flex-shrink-0">
            {other.photo_url && (
              <img loading="lazy" decoding="async" src={photoSrc(other.photo_url)} alt="" className={`w-full h-full object-cover ${!other.photo_unlocked ? "blur-md" : ""}`} />
            )}
          </div>
          <div className="min-w-0">
            <p className="font-medium truncate">{other.name}, {other.age}</p>
            <p className="text-xs text-muted-foreground truncate">{formatLastActive(other.last_active_minutes, t, other.online)}</p>
          </div>
        </Link>
        <div className="relative">
          <button data-testid="chat-menu" onClick={() => setMenuOpen((v) => !v)} className="p-2 rounded-full hover:bg-muted" aria-label="menu">
            <MoreVertical className="w-4 h-4" />
          </button>
          {menuOpen && (
            <div data-testid="chat-menu-dropdown" className="absolute right-0 top-10 z-40 bg-card border border-border rounded-2xl shadow-elevated w-44 py-1">
              <button data-testid="chat-block" onClick={blockUser} className="w-full text-left flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted">
                <Ban className="w-4 h-4 text-primary" /> {t("block")}
              </button>
              <button data-testid="chat-report" onClick={() => { setReportOpen(true); setMenuOpen(false); }} className="w-full text-left flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted">
                <Flag className="w-4 h-4 text-primary" /> {t("report")}
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="flex-1 px-4 py-4 space-y-2" data-testid="chat-history">
        {messages.length === 0 && (
          <div className="text-center py-12 text-muted-foreground text-sm">
            👋
          </div>
        )}
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex ${m.from_user_id === user?.id ? "justify-end" : "justify-start"}`}
          >
            <div className={`max-w-[75%] rounded-2xl px-3.5 py-2 text-sm ${
              m.from_user_id === user?.id
                ? "bg-primary text-white rounded-br-sm"
                : "bg-card border border-border rounded-bl-sm"
            } ${m.kind === "gift" ? "bg-gold-light text-yellow-900 border-gold/40" : ""} ${m.kind === "super" ? "ring-2 ring-gold" : ""} ${m.kind === "rose" ? "ring-2 ring-pink-500 bg-pink-50 text-pink-900 dark:bg-pink-900/20 dark:text-pink-100" : ""}`}>
              {m.kind === "super" && <span className="text-[9px] uppercase tracking-wider opacity-70 block">{t("super_application")}</span>}
              {m.kind === "rose" && <span className="text-[9px] uppercase tracking-wider opacity-70 block">🌹</span>}
              {m.kind === "voice" && m.meta?.voice_url ? (
                <div className="flex items-center gap-2 min-w-[200px]" data-testid={`voice-msg-${m.id}`}>
                  <span className="text-[9px] uppercase tracking-wider opacity-70">🎙 · {m.meta.voice_duration || 0}s</span>
                  <audio controls preload="none" src={`/api/chat/voice/${m.id}?auth=${localStorage.getItem("fidem_token") || ""}`} className="h-8 max-w-full" />
                </div>
              ) : (
                m.text
              )}
            </div>
          </div>
        ))}
        <div ref={endRef} />
      </div>

      {showTemplates && messages.length === 0 && (
        <div className="px-4 pb-2 space-y-1.5">
          {[t("greeting_1"), t("greeting_2"), t("greeting_3")].map((g, i) => (
            <button
              key={i}
              data-testid={`template-${i}`}
              onClick={() => send(g)}
              className="w-full text-left bg-muted hover:bg-border rounded-2xl px-3 py-2 text-sm"
            >
              {g}
            </button>
          ))}
        </div>
      )}

      {messages.length > 0 && messages.length < 6 && icebreakers.length > 0 && (
        <div className="px-4 pb-2" data-testid="icebreaker-chips">
          <div className="flex items-center justify-between mb-1.5">
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{t("suggestion_chip")}</p>
            <button data-testid="ai-icebreaker-btn" onClick={genAiIcebreakers} disabled={aiLoading} className="text-[10px] uppercase tracking-wider text-secondary hover:underline disabled:opacity-50 inline-flex items-center gap-1">
              <Wand2 className="w-3 h-3" /> {aiLoading ? t("ai_preparing") : t("ai_generate_short")}
            </button>
          </div>
          <div className="flex gap-1.5 overflow-x-auto no-scrollbar">
            {icebreakers.slice(0, 5).map((q, i) => (
              <button
                key={i}
                data-testid={`icebreaker-${i}`}
                onClick={() => setText(q)}
                className="whitespace-nowrap rounded-full border border-border bg-card hover:bg-muted px-3 py-1.5 text-xs"
              >
                {q.length > 35 ? q.slice(0, 35) + "…" : q}
              </button>
            ))}
          </div>
        </div>
      )}

      {messages.length === 0 && (
        <div className="px-4 pb-2">
          <button data-testid="ai-icebreaker-empty-btn" onClick={genAiIcebreakers} disabled={aiLoading} className="w-full rounded-2xl border border-dashed border-secondary/40 bg-secondary/5 hover:bg-secondary/10 py-2.5 text-xs text-secondary font-medium inline-flex items-center justify-center gap-1.5 disabled:opacity-50">
            <Wand2 className="w-3.5 h-3.5" /> {aiLoading ? t("ai_preparing") : t("ai_suggest")}
          </button>
        </div>
      )}

      <div className="fixed bottom-0 inset-x-0 glass border-t border-border/60 max-w-2xl xl:max-w-3xl mx-auto md:left-64 lg:left-72 md:right-0" style={{ paddingBottom: "env(safe-area-inset-bottom)", zIndex: 10000 }}>
        <div className="p-3 space-y-2">
          {/* Paywall banner (shown above the input — input remains visible & disabled) */}
          {access && access.requires_unlock && (
            <div data-testid="chat-paywall" className="rounded-2xl bg-gold/10 border border-gold/40 p-3 space-y-2">
              <p className="text-sm font-medium">{t("chat_locked_title")}</p>
              <p className="text-xs text-muted-foreground">
                {t("chat_locked_desc")} · 🛡 {access.guarantee_hours}h {t("guarantee")}
              </p>
              <p className="text-xs text-secondary mt-2">{t("chat_match_tip")}</p>
              <div className="grid grid-cols-1 gap-2 pt-1">
                {access.free_credits > 0 && (
                  <button data-testid="unlock-credit" onClick={() => unlockChat("credit")} disabled={unlocking}
                    className="w-full rounded-xl bg-secondary text-white text-sm py-2.5 font-medium disabled:opacity-50">
                    🎁 {t("use_free_credit")} ({access.free_credits})
                  </button>
                )}
                <button data-testid="unlock-balance" onClick={() => unlockChat("balance")} disabled={unlocking || access.balance < access.price_uzs}
                  className="w-full rounded-xl bg-primary text-white text-sm py-2.5 font-medium disabled:opacity-50">
                  💳 {t("unlock_one_time")} · {access.price_uzs.toLocaleString()} {t("sum")}
                </button>
                <Link to="/premium?tab=plans" data-testid="unlock-upgrade" className="w-full text-center rounded-xl border border-primary/40 text-primary text-sm py-2.5 font-medium">
                  ⭐ {t("or_subscribe")}
                </Link>
              </div>
            </div>
          )}
          {/* Always-visible message composer (disabled when locked) */}
          <div className="flex items-end gap-1.5 min-w-0">
            <button data-testid="rose-open" onClick={() => setRoseOpen(true)} disabled={access?.requires_unlock} className="shrink-0 w-10 h-10 grid place-items-center rounded-full bg-primary/10 hover:bg-primary/20 disabled:opacity-40 text-base" title="🌹">
              🌹
            </button>
            <button data-testid="gift-open" onClick={() => setGiftOpen(true)} disabled={access?.requires_unlock} className="shrink-0 w-10 h-10 grid place-items-center rounded-full bg-muted hover:bg-border disabled:opacity-40" title={t("send_gift")}>
              <Gift className="w-4 h-4" />
            </button>
            {!access?.requires_unlock && <div className="shrink-0"><ChatVoiceRecorder onSend={sendVoice} /></div>}
            <input
              data-testid="chat-input"
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !access?.requires_unlock && send()}
              disabled={!!access?.requires_unlock}
              placeholder={access?.requires_unlock ? t("chat_locked_inline") : t("type_message")}
              className="flex-1 min-w-0 rounded-full border border-border bg-card px-4 h-10 text-sm outline-none focus:border-primary disabled:opacity-60 disabled:cursor-not-allowed"
            />
            <button
              data-testid="chat-send"
              onClick={() => send()}
              disabled={sending || !text.trim() || !!access?.requires_unlock}
              className="shrink-0 w-10 h-10 grid place-items-center rounded-full bg-primary text-white disabled:opacity-50"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
      {giftOpen && <GiftModal targetId={otherId} targetName={other.name} onClose={() => setGiftOpen(false)} onSent={load} />}
      {roseOpen && <RoseModal targetId={otherId} targetName={other.name} onClose={() => setRoseOpen(false)} onSent={load} />}
      {reportOpen && <ReportModal t={t} onClose={() => setReportOpen(false)} onSubmit={reportUser} />}
    </div>
  );
}

function ReportModal({ t, onClose, onSubmit }) {
  const [reason, setReason] = useState("");
  const [custom, setCustom] = useState("");
  const reasons = [
    { id: "spam", label: t("report_reason_spam") },
    { id: "inappropriate", label: t("report_reason_inappropriate") },
    { id: "fake", label: t("report_reason_fake") },
    { id: "harassment", label: t("report_reason_harassment") },
    { id: "other", label: t("report_reason_other") },
  ];
  const submit = () => {
    const final = reason === "other" ? (custom || "").trim() : (reasons.find((r) => r.id === reason)?.label || "");
    if (!final) return;
    onSubmit(final);
  };
  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center" data-testid="report-modal">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative w-full max-w-md bg-card rounded-t-3xl sm:rounded-3xl p-6 mx-auto">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-heading text-lg font-semibold flex items-center gap-2"><Flag className="w-5 h-5 text-primary" /> {t("report_modal_title")}</h3>
          <button onClick={onClose} className="p-2 rounded-full hover:bg-muted" data-testid="report-close">✕</button>
        </div>
        <p className="text-xs text-muted-foreground mb-3">{t("report_modal_hint")}</p>
        <div className="space-y-1.5 mb-3">
          {reasons.map((r) => (
            <button
              key={r.id}
              data-testid={`report-reason-${r.id}`}
              onClick={() => setReason(r.id)}
              className={`w-full text-left rounded-xl border px-3 py-2.5 text-sm transition ${reason === r.id ? "border-primary bg-primary/5 text-primary" : "border-border bg-card hover:bg-muted"}`}
            >
              {r.label}
            </button>
          ))}
        </div>
        {reason === "other" && (
          <textarea
            data-testid="report-custom"
            value={custom}
            onChange={(e) => setCustom(e.target.value)}
            rows={3}
            className="w-full rounded-xl border border-border bg-card px-3 py-2 text-sm outline-none focus:border-primary mb-3"
            placeholder="..."
          />
        )}
        <button
          data-testid="report-submit"
          onClick={submit}
          disabled={!reason || (reason === "other" && !custom.trim())}
          className="w-full rounded-2xl bg-primary text-white font-medium py-3 disabled:opacity-50"
        >
          {t("report_send")}
        </button>
      </div>
    </div>
  );
}
