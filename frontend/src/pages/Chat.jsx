import React, { useEffect, useRef, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import GiftModal from "@/components/GiftModal";
import GiftCelebration, { tierFromPrice } from "@/components/GiftCelebration";
import ChatVoiceRecorder from "@/components/ChatVoiceRecorder";
import { ArrowLeft, Send, Gift, MoreVertical, Ban, Flag, Wand2, Play, Check, CheckCheck, Contact, AlertTriangle, X } from "lucide-react";
import { photoSrc } from "@/lib/photo";
import { formatLastActive } from "@/lib/time";
import { tapLight } from "@/lib/haptics";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import { QK } from "@/hooks/queries";
import { openExternalLink } from "@/lib/telegram";

// Mirrors the Standard plan price in Premium.jsx — shown next to the one-time
// unlock so the user can compare "pay once" vs "unlimited messaging".
const STANDARD_PRICE = 34900;

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
  const [access, setAccess] = useState(null);
  const [unlocking, setUnlocking] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [giftOpen, setGiftOpen] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);
  const [icebreakers, setIcebreakers] = useState([]);
  const [aiLoading, setAiLoading] = useState(false);
  const [messagesLoaded, setMessagesLoaded] = useState(false);
  const [celebration, setCelebration] = useState(null);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const endRef = useRef(null);
  const topRef = useRef(null);
  const aiAutoRef = useRef(false);

  const chatId = user && otherId ? [user.id, otherId].sort().join("_") : null;
  const { wsEvent, lang } = useApp();

  useEffect(() => {
    api.get(`/icebreakers?lang=${lang || "uz"}`).then((r) => setIcebreakers(r.data || [])).catch(() => {});
  }, [lang]);

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

  const loadOlderMessages = async () => {
    if (loadingOlder || messages.length === 0 || !chatId) return;
    setLoadingOlder(true);
    try {
      // Load 50 more messages before the oldest one we have
      const oldestTime = messages[0]?.created_at;
      const response = await api.get(`/messages/${chatId}?limit=50`);
      if (response.data && response.data.length > 0) {
        // Filter out duplicates and prepend older messages
        const newMsgs = response.data.filter(m => !messages.find(x => x.id === m.id));
        if (newMsgs.length > 0) {
          setMessages([...newMsgs, ...messages]);
        }
      }
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
        if (r.data?.payment_link) openExternalLink(r.data.payment_link);
        toast.info(t("redirecting_payment") || "To'lov sahifasiga o'tilmoqda...");
      } else {
        await api.post("/chat/unlock", { target_id: otherId, method });
        toast.success(t("chat_unlocked") || "Suhbat ochildi ✅");
        await refreshAccess();
      }
    } catch (err) {
      const detail = (err?.response?.data?.detail || "").toString();
      if (detail === "click_disabled") {
        toast.info(t("click_disabled_error"));
        nav("/premium?tab=balance");
      } else {
        toast.error("Error");
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

  // Subscribe straight from chat: create the Standard payment and open CLICK,
  // instead of bouncing to the plans page to pick again.
  const subscribeStandard = async () => {
    if (unlocking) return;
    setUnlocking(true);
    try {
      const r = await api.post("/payments/create", { purpose: "standard", amount: STANDARD_PRICE });
      if (r.data?.status === "paid") {
        toast.success(t("payment_success"));
        await refreshAccess();
      } else if (r.data?.payment_link) {
        openExternalLink(r.data.payment_link);
        toast.info(t("redirecting_payment") || "To'lov sahifasiga o'tilmoqda...");
      }
    } catch (err) {
      const detail = (err?.response?.data?.detail || "").toString();
      if (detail === "click_disabled") {
        toast.info(t("click_disabled_error"));
        nav("/premium?tab=balance");
      } else {
        toast.error(t("error_generic") || "Error");
      }
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

  // Empty chat: fetch AI-personalized first-message suggestions automatically
  // (once per chat open) so the user doesn't have to know a button exists.
  useEffect(() => {
    if (aiAutoRef.current) return;
    if (!messagesLoaded || messages.length > 0) return;
    if (!access || access.requires_unlock) return;
    aiAutoRef.current = true;
    genAiIcebreakers();
    // eslint-disable-next-line
  }, [messagesLoaded, messages.length, access]);

  // Off-platform contact detection (mirrors backend detect_contact_info).
  // Free plan: sharing contacts is a paid perk — blocked with an upsell.
  // Paid plans: allowed, but a compact confirm bar appears first so nobody
  // leaks their phone number with an accidental Enter.
  const CONTACT_RE = /(\+?998[\s-]?\d{2}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2})|(\d{2}[\s-]\d{3}[\s-]\d{2}[\s-]\d{2})|(\d{9,12})|(t\.me\/|telegram\.me\/|wa\.me\/|instagram\.com\/)|(@[a-z0-9_.]{4,})|(telegram)|(\btg\b)|(insta)|(whats?app)|(vatsap)|(viber)|(\bimo\b)|(raqam\w*\s*(ber|yubor|yoz|tashla))|(nomer)|(телефон)|(номер)|(телеграм)|(инстаграм)|(ватсап)|((?:\b(?:nol|bir|ikki|uch|to['’ʻ`]?rt|besh|olti|yetti|sakkiz|to['’ʻ`]?qqiz|o['’ʻ`]?n|yigirma|o['’ʻ`]?ttiz|qirq|ellik|oltmish|yetmish|sakson|to['’ʻ`]?qson|yuz)\b[\s,.-]*){4,})|((?:\b(?:ноль|один|одна|два|две|три|четыре|пять|шесть|семь|восемь|девять|десять|двадцать|тридцать|сорок|пятьдесят|шестьдесят|семьдесят|восемьдесят|девяносто|сто)\b[\s,.-]*){4,})/i;
  const [contactConfirm, setContactConfirm] = useState(null); // text awaiting confirm
  const [shareOpen, setShareOpen] = useState(false);
  const isPaidPlan = ["standard", "premium", "vip"].includes(user?.plan);

  const send = async (txt, opts = {}) => {
    const finalText = txt ?? text;
    if (!finalText.trim()) return;
    if (!opts.skipContactCheck && CONTACT_RE.test(finalText)) {
      if (!isPaidPlan) {
        toast.error(t("contact_free_blocked_error"));
        return;
      }
      setContactConfirm(finalText);
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

    setSending(true);
    try {
      const r = await api.post("/messages/send", { to_user_id: otherId, text: finalText });
      // Swap the temp bubble for the server's confirmed copy directly - don't
      // wait on the WebSocket echo to know the message made it. The WS
      // dedup check (by id) below already ignores it if it arrives after.
      setMessages((prev) => prev.map((m) => (m.id === tempMsg.id ? r.data : m)));
    } catch (e) {
      console.error("Send message error:", e);
      const detail = (e.response?.data?.detail || "").toString();
      toast.error(detail === "contact_free_blocked" ? t("contact_free_blocked_error") : (detail || e.message || t("error")));
      setMessages((prev) => prev.filter((m) => m.id !== tempMsg.id));
      load();
    } finally { setSending(false); }
  };

  // "Share my contact" — composes a message from the contacts saved in
  // Sozlamalar (phone / telegram / instagram) and sends it through the same
  // confirm flow.
  const savedContacts = [
    user?.contact_phone && `📞 ${user.contact_phone}`,
    user?.contact_telegram && `Telegram: @${String(user.contact_telegram).replace(/^@/, "")}`,
    user?.contact_instagram && `Instagram: @${String(user.contact_instagram).replace(/^@/, "")}`,
  ].filter(Boolean);
  const shareContacts = () => {
    if (!isPaidPlan) {
      toast.error(t("contact_free_blocked_error"));
      return;
    }
    setShareOpen(false);
    setContactConfirm(savedContacts.join(" · "));
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
        {messages.length > 0 && messages.length >= 50 && (
          <button
            ref={topRef}
            onClick={loadOlderMessages}
            disabled={loadingOlder}
            className="text-xs text-muted-foreground hover:text-secondary disabled:opacity-50 self-center py-2 transition"
          >
            {loadingOlder ? "⏳ Murakkab..." : "← Eski xabarlar"}
          </button>
        )}
        {messages.length === 0 && (
          <div className="text-center py-12 text-muted-foreground text-sm">
            👋
          </div>
        )}
        {messages.map((m) => {
          const mine = m.from_user_id === user?.id;
          return (
            <div key={m.id} className={`flex flex-col ${mine ? "items-end" : "items-start"}`}>
              <div className={`max-w-[75%] rounded-2xl px-3.5 py-2 text-sm ${
                mine
                  ? "bg-primary text-white rounded-br-sm"
                  : "bg-card border border-border rounded-bl-sm"
              } ${m.kind === "gift" ? "bg-gold-light text-yellow-900 border-gold/40" : ""}`}>
                {m.kind === "voice" && m.meta?.voice_url ? (
                  <div className="flex items-center gap-2 min-w-[200px]" data-testid={`voice-msg-${m.id}`}>
                    <span className="text-[9px] uppercase tracking-wider opacity-70">🎙 · {m.meta.voice_duration || 0}s</span>
                    <audio controls preload="none" src={`/api/chat/voice/${m.id}?auth=${localStorage.getItem("fidem_token") || ""}`} className="h-8 max-w-full" />
                  </div>
                ) : (
                  m.text
                )}
              </div>
              <div className={`flex items-center gap-1 mt-0.5 px-1 text-[10px] text-muted-foreground ${mine ? "flex-row-reverse" : ""}`} data-testid={`msg-meta-${m.id}`}>
                <span>{formatMsgTime(m.created_at)}</span>
                {mine && !m.sending && (
                  m.read
                    ? <CheckCheck className="w-3 h-3 text-secondary" />
                    : <Check className="w-3 h-3" />
                )}
              </div>
            </div>
          );
        })}
        <div ref={endRef} />
      </div>

      {/* Empty chat: AI writes the first message for you — suggestions load
          automatically (see the auto-effect above), tap one to put it in the
          composer, edit if you like, send. The old canned template texts are
          gone on purpose. */}
      {messagesLoaded && messages.length === 0 && !access?.requires_unlock && (
        <div className="px-4 pb-2 space-y-1.5" data-testid="ai-first-message">
          <div className="flex items-center justify-between">
            <p className="text-[10px] uppercase tracking-wider text-secondary font-semibold inline-flex items-center gap-1">
              <Wand2 className="w-3 h-3" /> {t("ai_first_message_title")}
            </p>
            <button data-testid="ai-icebreaker-btn" onClick={genAiIcebreakers} disabled={aiLoading} className="text-[10px] uppercase tracking-wider text-muted-foreground hover:text-secondary disabled:opacity-50">
              ↻ {t("ai_generate_short")}
            </button>
          </div>
          {aiLoading && icebreakers.length === 0 && (
            <div className="rounded-2xl bg-secondary/5 border border-dashed border-secondary/30 px-3 py-2.5 text-xs text-secondary animate-pulse">
              {t("ai_preparing")}
            </div>
          )}
          {icebreakers.slice(0, 3).map((q, i) => (
            <button
              key={i}
              data-testid={`icebreaker-${i}`}
              onClick={() => setText(q)}
              className="w-full text-left rounded-2xl border border-secondary/25 bg-secondary/5 hover:bg-secondary/10 px-3 py-2.5 text-sm"
            >
              {q}
            </button>
          ))}
        </div>
      )}

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
                  <p className="text-[10px] uppercase tracking-wide text-primary font-semibold">Standard</p>
                  <p className="font-heading text-lg font-bold tabular-nums leading-tight mt-0.5">
                    {STANDARD_PRICE.toLocaleString()}<span className="text-[10px] font-medium opacity-60"> {t("sum")}{t("plan_per_month")}</span>
                  </p>
                  <p className="text-[10px] text-secondary mt-0.5 leading-tight font-medium">{t("chat_unlimited_desc")}</p>
                  <span className="mt-2 block text-center rounded-lg bg-primary text-white text-xs py-1.5 font-semibold">{t("pay_with_click")}</span>
                </button>
              </div>
            </div>
          )}
          {/* Free weekly conversation hint — the composer is already open; this
              just tells the free user this one is on the house, so they notice
              when it's spent and understand the upgrade. */}
          {access?.uses_free_weekly && (
            <p data-testid="chat-free-weekly-hint" className="text-[11px] text-secondary text-center">{t("chat_free_weekly_hint")}</p>
          )}
          {/* Contact-share confirm — compact one-liner, never covers the chat */}
          {contactConfirm && (
            <div data-testid="contact-confirm" className="flex items-center gap-2 rounded-2xl bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-800 px-3 py-2">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
              <p className="text-[11px] text-amber-800 dark:text-amber-300 flex-1 min-w-0 truncate">{t("contact_confirm_hint")}</p>
              <button
                data-testid="contact-confirm-send"
                onClick={() => { const msg = contactConfirm; setContactConfirm(null); setText(""); send(msg, { skipContactCheck: true }); }}
                className="shrink-0 rounded-full bg-amber-600 text-white text-[11px] font-semibold px-3 py-1"
              >
                {t("send")}
              </button>
              <button data-testid="contact-confirm-cancel" onClick={() => setContactConfirm(null)} className="shrink-0 p-1 rounded-full hover:bg-amber-100 dark:hover:bg-amber-900">
                <X className="w-3.5 h-3.5 text-amber-700" />
              </button>
            </div>
          )}
          {/* Contact-share sheet — compact */}
          {shareOpen && (
            <div data-testid="contact-share-panel" className="flex items-center gap-2 rounded-2xl bg-card border border-border px-3 py-2">
              {savedContacts.length > 0 ? (
                <>
                  <p className="text-[11px] text-muted-foreground flex-1 min-w-0 truncate">{savedContacts.join(" · ")}</p>
                  <button data-testid="contact-share-send" onClick={shareContacts} className="shrink-0 rounded-full bg-primary text-white text-[11px] font-semibold px-3 py-1">{t("contact_share_cta")}</button>
                </>
              ) : (
                <Link to="/me/settings" className="text-[11px] text-primary underline flex-1">{t("contact_share_empty")}</Link>
              )}
              <button onClick={() => setShareOpen(false)} className="shrink-0 p-1 rounded-full hover:bg-muted"><X className="w-3.5 h-3.5" /></button>
            </div>
          )}
          {/* Always-visible message composer (disabled when locked) */}
          <div className="flex items-end gap-1.5 min-w-0">
            <button data-testid="gift-open" onClick={() => setGiftOpen(true)} disabled={access?.requires_unlock} className="shrink-0 w-10 h-10 grid place-items-center rounded-full bg-muted hover:bg-border disabled:opacity-40" title={t("send_gift")}>
              <Gift className="w-4 h-4" />
            </button>
            <button
              data-testid="contact-share-open"
              onClick={() => { setShareOpen((v) => !v); setContactConfirm(null); }}
              disabled={access?.requires_unlock}
              className="shrink-0 w-10 h-10 grid place-items-center rounded-full bg-muted hover:bg-border disabled:opacity-40"
              title={t("contact_share_cta")}
            >
              <Contact className="w-4 h-4" />
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
