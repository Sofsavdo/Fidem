import React, { useEffect, useRef, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import GiftModal from "@/components/GiftModal";
import RoseModal from "@/components/RoseModal";
import ChatVoiceRecorder from "@/components/ChatVoiceRecorder";
import { ArrowLeft, Send, Gift, MoreVertical, Ban, Flag, Wand2, Play } from "lucide-react";
import { photoSrc } from "@/lib/photo";
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
      const c = await api.get(`/candidates/${otherId}`);
      setOther(c.data);
      try {
        const a = await api.get(`/chat/access/${otherId}`);
        setAccess(a.data);
      } catch {
        /* keep access null → input shown by default */
      }
      if (chatId) {
        const m = await api.get(`/messages/${chatId}`);
        setMessages(m.data || []);
      }
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
      toast.error(err.response?.data?.detail || "Error");
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
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Xato");
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
      toast.success("Ovozli xabar yuborildi");
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Yuborib bo'lmadi");
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
      toast.success("AI savollar tayyor 🤖");
    } catch (e) {
      toast.error("AI hozir mavjud emas");
    } finally { setAiLoading(false); }
  };

  const blockUser = async () => {
    try {
      await api.post("/messages/block", { user_id: otherId });
      toast.success("Blokladingiz");
      setMenuOpen(false);
      nav("/messages");
    } catch (e) { toast.error("Xato"); }
  };
  const reportUser = async () => {
    const reason = window.prompt(t("report_reason"), "Spam");
    if (!reason) return;
    try {
      await api.post("/messages/report", { user_id: otherId, reason });
      toast.success(t("reported"));
      setMenuOpen(false);
    } catch (e) { toast.error("Xato"); }
  };

  if (!other) return <div className="p-6 text-center text-muted-foreground">{t("loading")}</div>;

  return (
    <div className="flex flex-col min-h-screen pb-24">
      <div className="sticky top-0 z-30 glass border-b border-border/60 px-4 py-3 flex items-center gap-3">
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
            <p className="text-xs text-muted-foreground truncate">{other.last_active_label}</p>
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
              <button data-testid="chat-report" onClick={reportUser} className="w-full text-left flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted">
                <Flag className="w-4 h-4 text-primary" /> {t("report")}
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="flex-1 px-4 py-4 space-y-2" data-testid="chat-history">
        {messages.length === 0 && (
          <div className="text-center py-12 text-muted-foreground text-sm">
            Birinchi xabaringizni yuboring 👋
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
            } ${m.kind === "gift" ? "bg-gold-light text-yellow-900 border-gold/40" : ""} ${m.kind === "super" ? "ring-2 ring-gold" : ""} ${m.kind === "rose" ? "ring-2 ring-primary bg-primary/10 text-primary" : ""}`}>
              {m.kind === "super" && <span className="text-[9px] uppercase tracking-wider opacity-70 block">Super</span>}
              {m.kind === "rose" && <span className="text-[9px] uppercase tracking-wider opacity-70 block">🌹 Atirgul</span>}
              {m.kind === "voice" && m.meta?.voice_url ? (
                <div className="flex items-center gap-2 min-w-[200px]" data-testid={`voice-msg-${m.id}`}>
                  <span className="text-[9px] uppercase tracking-wider opacity-70">🎙 Ovoz · {m.meta.voice_duration || 0}s</span>
                  <audio controls preload="none" src={m.meta.voice_url} className="h-8 max-w-full" />
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
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Suhbat boshlash uchun savol</p>
            <button data-testid="ai-icebreaker-btn" onClick={genAiIcebreakers} disabled={aiLoading} className="text-[10px] uppercase tracking-wider text-secondary hover:underline disabled:opacity-50 inline-flex items-center gap-1">
              <Wand2 className="w-3 h-3" /> {aiLoading ? "AI…" : "AI yaratish"}
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
            <Wand2 className="w-3.5 h-3.5" /> {aiLoading ? "AI tayyorlamoqda…" : "AI shaxsiy savol tavsiya etsin"}
          </button>
        </div>
      )}

      <div className="fixed bottom-0 inset-x-0 z-40 glass border-t border-border/60 max-w-2xl xl:max-w-3xl mx-auto md:left-64 lg:left-72 md:right-0">
        <div className="p-3">
          {access && access.requires_unlock ? (
            <div data-testid="chat-paywall" className="rounded-2xl bg-gold/10 border border-gold/40 p-3 space-y-2">
              <p className="text-sm font-medium">{t("chat_locked_title")}</p>
              <p className="text-xs text-muted-foreground">
                {t("chat_locked_desc")} · 🛡 {access.guarantee_hours}h {t("guarantee")}
              </p>
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
                <button data-testid="unlock-coins" onClick={() => unlockChat("coins")} disabled={unlocking || access.coins < access.price_coins}
                  className="w-full rounded-xl bg-card border border-border text-sm py-2.5 font-medium disabled:opacity-50">
                  🪙 {t("unlock_with_coins")} · {access.price_coins} coin ({access.coins})
                </button>
                <button data-testid="unlock-click" onClick={() => unlockChat("click")} disabled={unlocking}
                  className="w-full rounded-xl bg-muted text-sm py-2.5 font-medium disabled:opacity-50">
                  {t("pay_with_click")} · {access.price_uzs.toLocaleString()} {t("sum")}
                </button>
                <Link to="/premium" data-testid="unlock-upgrade" className="w-full text-center rounded-xl border border-primary/40 text-primary text-sm py-2.5 font-medium">
                  ⭐ {t("or_subscribe")}
                </Link>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <button data-testid="rose-open" onClick={() => setRoseOpen(true)} className="p-2.5 rounded-full bg-primary/10 hover:bg-primary/20" title="Atirgul yuborish">
                🌹
              </button>
              <button data-testid="gift-open" onClick={() => setGiftOpen(true)} className="p-2.5 rounded-full bg-muted hover:bg-border" title={t("send_gift")}>
                <Gift className="w-4 h-4" />
              </button>
              <ChatVoiceRecorder onSend={sendVoice} />
              <input
                data-testid="chat-input"
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && send()}
                placeholder={t("type_message")}
                className="flex-1 rounded-full border border-border bg-card px-4 py-2.5 outline-none focus:border-primary"
              />
              <button
                data-testid="chat-send"
                onClick={() => send()}
                disabled={sending || !text.trim()}
                className="p-2.5 rounded-full bg-primary text-white disabled:opacity-50"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>
      {giftOpen && <GiftModal targetId={otherId} targetName={other.name} onClose={() => setGiftOpen(false)} onSent={load} />}
      {roseOpen && <RoseModal targetId={otherId} targetName={other.name} onClose={() => setRoseOpen(false)} onSent={load} />}
    </div>
  );
}
