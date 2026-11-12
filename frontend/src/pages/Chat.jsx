import React, { useEffect, useRef, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { track } from "@/lib/analytics";
import { useApp } from "@/contexts/AppContext";
import GiftModal from "@/components/GiftModal";
import GiftCelebration, { tierFromPrice } from "@/components/GiftCelebration";
import { giftGradient } from "@/lib/giftVisuals";
import ChatVoiceRecorder from "@/components/ChatVoiceRecorder";
import { ArrowLeft, Send, Gift, MoreVertical, Ban, Flag, Play, Check, CheckCheck, Contact, ShieldAlert } from "lucide-react";
import { useContactExchange, ExchangePanel, IncomingExchange, AcceptedContacts } from "@/components/ContactExchange";
import { photoSrc } from "@/lib/photo";
import { formatLastActive } from "@/lib/time";
import { tapLight } from "@/lib/haptics";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import { QK, usePaymentConfig } from "@/hooks/queries";
import { startPayment, payErrorText, onPaid } from "@/lib/payFlow";
import { purchasePlan, PREMIUM_PERIODS_DEFAULT } from "@/lib/purchase";
import { FEATURES } from "@/lib/features";

// Mirrors the Standard plan price in Premium.jsx — shown next to the one-time
// unlock so the user can compare "pay once" vs "unlimited messaging".
const PREMIUM_FROM = PREMIUM_PERIODS_DEFAULT[1]; // cheapest Premium period (1 day)

function formatMsgTime(iso) {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

export default function Chat() {
  const { otherId } = useParams();
  const { user, t } = useApp();
  const nav = useNavigate();
  const queryClient = useQueryClient();
  // Seed the header from the profile-detail cache the candidate card prefetched,
  // so the chat opens instantly with the name/photo instead of a blank bar.
  const [other, setOther] = useState(() => queryClient.getQueryData(QK.candidateDetail(otherId)) || null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const sendLockRef = useRef(false);
  const paywallSeenRef = useRef(false);
  const [access, setAccess] = useState(null);
  const [unlocking, setUnlocking] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [giftOpen, setGiftOpen] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);
  const [messagesLoaded, setMessagesLoaded] = useState(false);
  const [celebration, setCelebration] = useState(null);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const endRef = useRef(null);
  const topRef = useRef(null);

  const chatId = user && otherId ? [user.id, otherId].sort().join("_") : null;
  const { wsEvent } = useApp();
  const { data: payCfg } = usePaymentConfig();
  const payOff = !!payCfg && !payCfg.payments_available; // no way to pay right now

  // Fire the three requests independently and paint each as it arrives, so the
  // header and messages show the moment they're ready rather than blocking on
  // the slowest request (the old Promise.all made the whole screen wait).
  const load = () => {
    api.get(`/candidates/${otherId}`).then((c) => setOther(c.data)).catch(() => {});
    api.get(`/chat/access/${otherId}`).then((a) => setAccess(a.data)).catch(() => {});
    if (chatId) {
      // Load messages with pagination (limit 50 per request, most recent first)
      api.get(`/messages/${chatId}?limit=50`)
        .then((m) => setMessages(m.data || []))
        .catch(() => {})
        .finally(() => setMessagesLoaded(true));
    } else {
      setMessagesLoaded(true);
    }
  };

  const [hasMoreOlder, setHasMoreOlder] = useState(true);

  const loadOlderMessages = async () => {
    if (loadingOlder || messages.length === 0 || !chatId || !hasMoreOlder) return;
    setLoadingOlder(true);
    try {
      // Cursor = created_at of the oldest message we already have.
      const before = messages[0]?.created_at;
      const response = await api.get(`/messages/${chatId}`, { params: { limit: 50, before } });
      const page = response.data || [];
      if (page.length < 50) setHasMoreOlder(false);
      const known = new Set(messages.map((x) => x.id));
      const newMsgs = page.filter((m) => !known.has(m.id));
      if (newMsgs.length > 0) setMessages((prev) => [...newMsgs, ...prev]);
    } catch (err) {
      console.error("Failed to load older messages:", err);
    } finally {
      setLoadingOlder(false);
    }
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
        startPayment(r.data, t);
      } else {
        await api.post("/chat/unlock", { target_id: otherId, method });
        toast.success(t("chat_unlocked") || "Suhbat ochildi ✅");
        await refreshAccess();
      }
    } catch (err) {
      const detail = (err?.response?.data?.detail || "").toString();
      if (detail === "click_disabled") {
        toast.info(t("click_disabled_error"));
        nav(`/premium?tab=balance&amount=${access?.price_uzs || 0}`);
      } else {
        toast.error(payErrorText(detail, t) || t("error_generic"));
      }
    } finally {
      setUnlocking(false);
    }
  };

  // One-time unlock: pay from balance if it covers the price, otherwise go
  // straight to CLICK — so the button always does something (before, it was
  // silently disabled when the balance was short).
  const payOneTime = () => {
    if (unlocking) return;
    if ((access?.balance || 0) >= (access?.price_uzs || 0)) unlockChat("balance");
    else unlockChat("click");
  };

  // Premium from the chat paywall: the quick picker (1 day / 15 days / month).
  const subscribeStandard = () => {
    if (unlocking) return;
    purchasePlan("premium", { source: "chat", reason: t("chat_unlimited_desc"), onPaid: refreshAccess });
  };

  useEffect(() => onPaid(() => { refreshAccess(); }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [otherId]);

  useEffect(() => {
    setHasMoreOlder(true);
    load();
    // eslint-disable-next-line
  }, [otherId, user?.id]);

  useEffect(() => { if (otherId) track("chat_opened"); }, [otherId]);
  useEffect(() => {
    if (access?.requires_unlock && !paywallSeenRef.current) {
      paywallSeenRef.current = true;
      track("chat_paywall_seen");
    }
  }, [access]);

  // Socket dropped and came back: pull whatever we missed meanwhile.
  useEffect(() => {
    if (wsEvent?.type !== "resync" || !chatId) return;
    api.get(`/messages/${chatId}?limit=50`).then((m) => setMessages(m.data || [])).catch(() => {});
    // eslint-disable-next-line
  }, [wsEvent, chatId]);

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
    // Receiving a gift deserves the same celebration as sending one - a
    // 499,000 so'm rocket landing in your chat shouldn't look like plain text.
    if (m.kind === "gift" && m.to_user_id === user?.id && m.meta) {
      setCelebration({ emoji: m.meta.emoji, label: m.meta.label, tier: tierFromPrice(m.meta.price || 0) });
    }
    // eslint-disable-next-line
  }, [wsEvent, chatId, user]);

  // The other side just opened this chat and read our messages - flip our
  // sent bubbles to "read" live instead of only on next reload.
  useEffect(() => {
    if (!wsEvent || wsEvent.type !== "read" || !chatId) return;
    const { chat_id, reader_id } = wsEvent.data || {};
    if (chat_id !== chatId || reader_id === user?.id) return;
    setMessages((prev) => prev.map((m) => (m.from_user_id === user?.id ? { ...m, read: true } : m)));
    // eslint-disable-next-line
  }, [wsEvent, chatId, user]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  // Off-platform contact detection (mirrors backend detect_contact_info).
  // Phone / Telegram / Instagram in a message is blocked for everyone; the
  // contact-exchange panel (both selfie-verified, real conversation, consent)
  // is the only way to swap contacts. Checking here keeps the typed text.
  const CONTACT_RE = /(\+?998[\s-]?\d{2}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2})|(\d{2}[\s-]\d{3}[\s-]\d{2}[\s-]\d{2})|(\d{9,12})|(t\.me\/|telegram\.me\/|wa\.me\/|instagram\.com\/)|(@[a-z0-9_.]{4,})|(telegram)|(\btg\b)|(insta)|(whats?app)|(vatsap)|(viber)|(\bimo\b)|(raqam\w*\s*(ber|yubor|yoz|tashla))|(nomer)|(телефон)|(номер)|(телеграм)|(инстаграм)|(ватсап)|((?:\b(?:nol|bir|ikki|uch|to['’ʻ`]?rt|besh|olti|yetti|sakkiz|to['’ʻ`]?qqiz|o['’ʻ`]?n|yigirma|o['’ʻ`]?ttiz|qirq|ellik|oltmish|yetmish|sakson|to['’ʻ`]?qson|yuz)\b[\s,.-]*){4,})|((?:\b(?:ноль|один|одна|два|две|три|четыре|пять|шесть|семь|восемь|девять|десять|двадцать|тридцать|сорок|пятьдесят|шестьдесят|семьдесят|восемьдесят|девяносто|сто)\b[\s,.-]*){4,})/i;
  const [shareOpen, setShareOpen] = useState(false);
  const { state: cx, reload: reloadCx } = useContactExchange(otherId);
  // Women write only after the live selfie check (fake female profiles).
  // AI conversation partners: labelled, free, text only, no contact exchange.
  const isAi = !!(other?.is_ai || access?.is_ai || String(otherId).startsWith("ai_"));
  const needsSelfie = !isAi && user?.gender === "female" && !user?.verified_selfie && !user?.is_admin;
  const openExchange = () => { setShareOpen(true); reloadCx(true); };
  useEffect(() => {
    if (cx?.status !== "accepted") reloadCx();
  }, [messages.length]); // eslint-disable-line react-hooks/exhaustive-deps

  const send = async (txt) => {
    const finalText = txt ?? text;
    if (!finalText.trim()) return;
    // Enter key-repeat / double tap can fire a second send before React has
    // re-rendered with the cleared input - a ref blocks that window.
    if (sendLockRef.current) return;
    if (needsSelfie) {
      toast.error(t("selfie_required_error"), { action: { label: t("selfie_start"), onClick: () => nav("/verification") } });
      return;
    }
    if (CONTACT_RE.test(finalText)) {
      toast.error(t("contact_use_button_error"));
      openExchange();
      return;
    }
    tapLight();

    // Optimistic UI update - show message immediately
    const tempMsg = {
      id: `temp-${Date.now()}`,
      from_user_id: user.id,
      text: finalText,
      kind: "text",
      created_at: new Date().toISOString(),
      sending: true,
    };
    setMessages((prev) => [...prev, tempMsg]);
    setText("");

    sendLockRef.current = true;
    setSending(true);
    try {
      const r = await api.post("/messages/send", { to_user_id: otherId, text: finalText });
      // Swap the temp bubble for the server's confirmed copy directly - don't
      // wait on the WebSocket echo to know the message made it. The WS
      // dedup check (by id) below already ignores it if it arrives after.
      // The WebSocket echo can land BEFORE this response; then the confirmed
      // message is already in the list and swapping the temp bubble in would
      // show the same message twice - just drop the temp copy instead.
      track("message_sent");
      setMessages((prev) => (
        prev.some((m) => m.id === r.data.id)
          ? prev.filter((m) => m.id !== tempMsg.id)
          : prev.map((m) => (m.id === tempMsg.id ? r.data : m))
      ));
    } catch (e) {
      console.error("Send message error:", e);
      const detail = (e.response?.data?.detail || "").toString();
      // Never show a raw backend code to the user.
      const known = {
        contact_use_button: "contact_use_button_error",
        money_request_blocked: "money_request_blocked_error",
        selfie_required: "selfie_required_error",
        message_blocked: "message_blocked_error",
        ai_off: "ai_off_error",
        ai_text_only: "ai_text_only_error",
        muted_temp: "muted_temp_error",
        photo_required: "photo_required_error",
        message_too_long: "msg_too_long_error",
        empty_message: "msg_empty_error",
        blocked: "msg_blocked_error",
        muted: "msg_muted_error",
      };
      if (detail === "selfie_required") {
        toast.error(t("selfie_required_error"), { action: { label: t("selfie_start"), onClick: () => nav("/verification") } });
      } else {
        toast.error(t(known[detail] || "error_generic"));
      }
      setMessages((prev) => prev.filter((m) => m.id !== tempMsg.id));
      // Give the text back so it can be fixed, not retyped.
      if (detail === "message_too_long" || detail === "contact_use_button" || detail === "message_blocked") setText(finalText);
      if (detail === "contact_use_button") openExchange();
      load();
    } finally { sendLockRef.current = false; setSending(false); }
  };

  const sendVoice = async ({ voice_url, voice_duration }) => {
    setSending(true);
    try {
      const r = await api.post("/messages/send", {
        to_user_id: otherId,
        text: "",
        kind: "voice",
        voice_url,
        voice_duration,
      });
      // Show the confirmed message immediately rather than waiting on the
      // WebSocket echo (same fix as text messages).
      setMessages((prev) => (prev.some((m) => m.id === r.data.id) ? prev : [...prev, r.data]));
        toast.success("✅");
    } catch (e) {
      console.error("Send voice error:", e);
      const errorMsg = e.response?.data?.detail || e.message || t("error");
      toast.error(errorMsg);
      load(); // Reload only on error
    } finally { setSending(false); }
  };

  const sendGift = (kind) => {
    setGiftOpen(true);
    // legacy quick-send kept for backward compat — not used now
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
            <p className="font-medium truncate">
              {other.ai_role === "assistant" || otherId === "ai_assistant" ? t("assistant_name") : `${other.name}, ${other.age}`}
              {isAi && <span data-testid="chat-ai-badge" className="ml-1.5 text-[10px] font-bold text-white bg-violet-600 rounded-full px-1.5 py-0.5 align-middle">🤖 AI</span>}
            </p>
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
                <Ban className="w-4 h-4 text-foreground" /> {t("block")}
              </button>
              <button data-testid="chat-report" onClick={() => { setReportOpen(true); setMenuOpen(false); }} className="w-full text-left flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted">
                <Flag className="w-4 h-4 text-foreground" /> {t("report")}
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="flex-1 px-4 py-4 space-y-2 overflow-y-auto flex flex-col" data-testid="chat-history">
        {messages.length >= 50 && hasMoreOlder && (
          <button
            ref={topRef}
            onClick={loadOlderMessages}
            disabled={loadingOlder}
            className="text-xs text-muted-foreground hover:text-secondary disabled:opacity-50 self-center py-2 transition"
          >
            {loadingOlder ? "⏳ ..." : "← Eski xabarlar"}
          </button>
        )}
        {isAi && (
          <p data-testid="chat-ai-note" className="self-center max-w-[92%] text-center text-[11px] text-violet-800 dark:text-violet-200 bg-violet-100 dark:bg-violet-950/50 rounded-2xl px-3 py-1.5">
            🤖 {otherId === "ai_assistant" ? t("assistant_chat_note") : t("ai_chat_note")}
          </p>
        )}
        <p data-testid="chat-safety" className="self-center max-w-[92%] text-center text-[11px] text-muted-foreground bg-muted/60 rounded-full px-3 py-1 inline-flex items-center gap-1">
          <ShieldAlert className="w-3 h-3 shrink-0" /> {t("chat_safety_line")}
        </p>
        {messages.length === 0 && (
          <div className="text-center py-12 text-muted-foreground text-sm">
            👋
          </div>
        )}
        {messages.map((m) => {
          const mine = m.from_user_id === user?.id;
          const footer = (
            <div className={`flex items-center gap-1 mt-0.5 px-1 text-[10px] text-muted-foreground ${mine ? "flex-row-reverse" : ""}`} data-testid={`msg-meta-${m.id}`}>
              <span>{formatMsgTime(m.created_at)}</span>
              {mine && !m.sending && (
                m.read
                  ? <CheckCheck className="w-3 h-3 text-secondary" />
                  : <Check className="w-3 h-3" />
              )}
            </div>
          );

          // A delivered gift renders as the SAME gradient card the Gift
          // Shop tile showed before it was bought - a plain emoji+text
          // bubble stopped reading as "a gift" the moment the live
          // celebration animation finished playing.
          if (m.kind === "gift" && m.meta) {
            return (
              <div key={m.id} className={`flex flex-col ${mine ? "items-end" : "items-start"}`}>
                <div
                  className={`relative overflow-hidden rounded-3xl w-40 p-3 flex flex-col text-white shadow-lg bg-gradient-to-br ${giftGradient(m.meta)}`}
                  data-testid={`gift-msg-${m.id}`}
                >
                  <span className="absolute inset-0 bg-gradient-to-br from-white/25 via-transparent to-black/10 pointer-events-none" />
                  <span className="relative self-start text-[9px] font-bold uppercase tracking-wider bg-black/25 backdrop-blur-sm px-2 py-0.5 rounded-full">🎁 Sovg'a</span>
                  <span className="relative grid place-items-center py-2.5">
                    <span className="absolute w-12 h-12 rounded-full bg-white/25 blur-xl" />
                    <span className="relative text-3xl drop-shadow-[0_4px_10px_rgba(0,0,0,0.35)]">{m.meta.emoji}</span>
                  </span>
                  <span className="relative text-center">
                    <p className="text-xs font-semibold leading-tight line-clamp-2">{m.meta.label}</p>
                    {/* "so'm" always on its own line - matches the Gift Shop
                        tile fix: a 6-digit price wrapping only sometimes
                        made cards look inconsistent. */}
                    <p className="text-sm font-bold tabular-nums mt-0.5 leading-tight">
                      {(m.meta.price || 0).toLocaleString()}
                      <span className="block text-[10px] font-medium opacity-80 leading-none mt-0.5">so'm</span>
                    </p>
                  </span>
                </div>
                {footer}
              </div>
            );
          }

          return (
            <div key={m.id} className={`flex flex-col ${mine ? "items-end" : "items-start"}`}>
              <div className={`max-w-[75%] rounded-2xl px-3.5 py-2 text-sm ${
                mine
                  ? "bg-primary text-white rounded-br-sm"
                  : "bg-card border border-border rounded-bl-sm"
              }`}>
                {m.kind === "voice" && m.meta?.voice_url ? (
                  <div className="flex items-center gap-2 min-w-[200px]" data-testid={`voice-msg-${m.id}`}>
                    <span className="text-[9px] uppercase tracking-wider opacity-70">🎙 · {m.meta.voice_duration || 0}s</span>
                    <audio controls preload="none" src={`/api/chat/voice/${m.id}?auth=${localStorage.getItem("fidem_token") || ""}`} className="h-8 max-w-full" />
                  </div>
                ) : m.kind === "video" && m.meta?.video_url ? (
                  // Video messages used to fall through to plain text and
                  // render as the literal string "[video]".
                  <video
                    controls
                    preload="none"
                    playsInline
                    src={photoSrc(m.meta.video_url)}
                    poster={m.meta.video_thumbnail ? photoSrc(m.meta.video_thumbnail) : undefined}
                    className="max-w-full max-h-64 rounded-xl"
                    data-testid={`video-msg-${m.id}`}
                  />
                ) : (
                  m.text
                )}
              </div>
              {footer}
            </div>
          );
        })}
        <div ref={endRef} />
      </div>

      <div className="fixed bottom-0 inset-x-0 glass border-t border-border/60 max-w-2xl xl:max-w-3xl mx-auto md:left-64 lg:left-72 md:right-0" style={{ paddingBottom: "env(safe-area-inset-bottom)", zIndex: 10000 }}>
        <div className="p-3 space-y-2">
          {/* Paywall banner (shown above the input — input remains visible & disabled) */}
          {access && access.requires_unlock && (
            <div data-testid="chat-paywall" className="rounded-2xl bg-card border border-border shadow-soft p-3 space-y-2.5">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-semibold">{t("chat_locked_title")}</p>
                <span className="text-[11px] text-muted-foreground shrink-0">🛡 {access.guarantee_hours}h {t("guarantee")}</span>
              </div>
              {/* Free-path explainer — replying to an incoming message and
                  mutual-save chat are both free. */}
              <p className="text-[11px] text-secondary leading-relaxed rounded-lg bg-secondary/8 border border-secondary/20 p-2">{t("chat_free_paths")}</p>

              {access.free_credits > 0 && (
                <button data-testid="unlock-credit" onClick={() => unlockChat("credit")} disabled={unlocking}
                  className="w-full rounded-xl bg-secondary text-white text-sm py-2.5 font-medium disabled:opacity-50">
                  🎁 {t("use_free_credit")} ({access.free_credits})
                </button>
              )}

              {payOff ? (
                <p data-testid="chat-pay-soon" className="text-[12px] leading-relaxed rounded-xl bg-muted/60 border border-border p-3">{t("chat_locked_no_pay")}</p>
              ) : (
                <>
              {/* Quick top-up balance link if balance is insufficient */}
              {access.balance < access.price_uzs && (
                <Link to="/premium?tab=balance" data-testid="chat-topup-balance"
                  className="block w-full rounded-xl border border-primary/40 bg-primary/5 text-primary text-sm py-2.5 font-medium text-center hover:bg-primary/10 active:scale-[0.98] transition">
                  💳 {t("insufficient_balance")} → {t("topup_balance")}
                </Link>
              )}

              {/* Drawn comparison: pay-once vs unlimited */}
              <div className="grid grid-cols-2 gap-2">
                <button
                  data-testid="unlock-balance"
                  onClick={payOneTime}
                  disabled={unlocking}
                  className="rounded-xl border border-border bg-card p-2.5 text-left transition active:scale-[0.98] disabled:opacity-50"
                >
                  <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{t("chat_onetime_label")}</p>
                  <p className="font-heading text-lg font-bold tabular-nums leading-tight mt-0.5">
                    {access.price_uzs.toLocaleString()}<span className="text-[10px] font-medium opacity-60"> {t("sum")}</span>
                  </p>
                  <p className="text-[10px] text-muted-foreground mt-0.5 leading-tight">{t("chat_onetime_desc")}</p>
                  <span className="mt-2 block text-center rounded-lg border border-primary/50 text-primary text-xs py-1.5 font-semibold">
                    {access.balance >= access.price_uzs ? t("chat_pay_now") : t("pay_with_click")}
                  </span>
                </button>

                <button
                  onClick={subscribeStandard}
                  disabled={unlocking}
                  data-testid="unlock-upgrade"
                  className="relative rounded-xl border-2 border-primary bg-primary/5 p-2.5 text-left transition active:scale-[0.98] disabled:opacity-50"
                >
                  <span className="absolute -top-2 right-2 rounded-full bg-primary text-white text-[8px] font-bold px-1.5 py-0.5 uppercase tracking-wide">{t("best_value")}</span>
                  <p className="text-[10px] uppercase tracking-wide text-primary font-semibold">Premium</p>
                  <p className="font-heading text-lg font-bold tabular-nums leading-tight mt-0.5">
                    <span className="text-sm">{t("price_per_day_from").replace("{price}", PREMIUM_FROM.toLocaleString())}</span>
                  </p>
                  <p className="text-[10px] text-secondary mt-0.5 leading-tight font-medium">{t("chat_unlimited_desc")}</p>
                  <span className="mt-2 block text-center rounded-lg bg-primary text-white text-xs py-1.5 font-semibold">{t("pay_with_click")}</span>
                </button>
              </div>
                </>
              )}
            </div>
          )}
          {/* Free weekly conversation hint — the composer is already open; this
              just tells the free user this one is on the house, so they notice
              when it's spent and understand the upgrade. */}
          {access?.uses_free_weekly && (
            <p data-testid="chat-free-weekly-hint" className="text-[11px] text-secondary text-center">{t("chat_free_weekly_hint")}</p>
          )}
          {!isAi && <IncomingExchange state={cx} otherId={otherId} otherName={other.name} onAnswered={() => reloadCx(true)} />}
          {!shareOpen && <AcceptedContacts state={cx} />}
          {shareOpen && <ExchangePanel state={cx} otherId={otherId} onClose={() => setShareOpen(false)} onChanged={() => reloadCx(true)} />}
          {needsSelfie && (
            <Link to="/verification" data-testid="chat-selfie-gate" className="block rounded-2xl border border-secondary/40 bg-secondary/10 px-3 py-2 text-xs">
              📸 {t("selfie_required_error")} <span className="underline font-medium">{t("selfie_start")}</span>
            </Link>
          )}
          {/* Always-visible message composer (disabled when locked) */}
          <div className="flex items-end gap-1.5 min-w-0">
            {FEATURES.giftShop && (
              <button data-testid="gift-open" onClick={() => setGiftOpen(true)} disabled={access?.requires_unlock} className="shrink-0 w-10 h-10 grid place-items-center rounded-full bg-muted hover:bg-border disabled:opacity-40" title={t("send_gift")}>
              <Gift className="w-4 h-4" />
            </button>
            )}
            {!isAi && (
            <button
              data-testid="contact-share-open"
              onClick={() => (shareOpen ? setShareOpen(false) : openExchange())}
              disabled={access?.requires_unlock}
              className="shrink-0 w-10 h-10 grid place-items-center rounded-full bg-muted hover:bg-border disabled:opacity-40"
              title={t("cx_request")}
            >
              <Contact className="w-4 h-4" />
            </button>
            )}
            {!access?.requires_unlock && !isAi && <div className="shrink-0"><ChatVoiceRecorder onSend={sendVoice} /></div>}
            <input
              data-testid="chat-input"
              maxLength={2000}
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.repeat && !e.nativeEvent?.isComposing && !access?.requires_unlock && send()}
              disabled={!!access?.requires_unlock || !!access?.blocked}
              placeholder={access?.blocked ? t("user_blocked_error") : access?.requires_unlock ? t("chat_locked_inline") : t("type_message")}
              className="flex-1 min-w-0 rounded-full border border-border bg-card px-4 h-10 text-sm outline-none focus:border-primary disabled:opacity-60 disabled:cursor-not-allowed"
            />
            <button
              data-testid="chat-send"
              onClick={() => send()}
              disabled={sending || !text.trim() || !!access?.requires_unlock || !!access?.blocked}
              className="shrink-0 w-10 h-10 grid place-items-center rounded-full bg-primary text-white disabled:opacity-50"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
      {giftOpen && (
        <GiftModal
          targetId={otherId}
          targetName={other.name}
          onClose={() => setGiftOpen(false)}
          onSent={(item) => { load(); setCelebration(item); }}
        />
      )}
      {reportOpen && <ReportModal t={t} onClose={() => setReportOpen(false)} onSubmit={reportUser} />}
      <GiftCelebration gift={celebration} onDone={() => setCelebration(null)} />
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
    <div className="fixed inset-0 flex items-end sm:items-center justify-center" style={{ zIndex: 10001 }} data-testid="report-modal">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative w-full max-w-md bg-card rounded-t-3xl sm:rounded-3xl p-6 mx-auto">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-heading text-lg font-semibold flex items-center gap-2"><Flag className="w-5 h-5 text-foreground" /> {t("report_modal_title")}</h3>
          <button onClick={onClose} className="p-2 rounded-full hover:bg-muted" data-testid="report-close">✕</button>
        </div>
        <p className="text-xs text-muted-foreground mb-3">{t("report_modal_hint")}</p>
        <div className="space-y-1.5 mb-3">
          {reasons.map((r) => (
            <button
              key={r.id}
              data-testid={`report-reason-${r.id}`}
              onClick={() => setReason(r.id)}
              className={`w-full text-left rounded-xl border px-3 py-2.5 text-sm transition ${reason === r.id ? "border-primary bg-primary/5 text-foreground" : "border-border bg-card hover:bg-muted"}`}
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
