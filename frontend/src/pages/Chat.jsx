import React, { useEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { ArrowLeft, Send, Gift, Sparkles } from "lucide-react";
import { toast } from "sonner";

export default function Chat() {
  const { otherId } = useParams();
  const { user, t } = useApp();
  const [other, setOther] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [showTemplates, setShowTemplates] = useState(true);
  const [cannotMessage, setCannotMessage] = useState(false);
  const endRef = useRef(null);

  const chatId = user && otherId ? [user.id, otherId].sort().join("_") : null;

  const load = async () => {
    try {
      const c = await api.get(`/candidates/${otherId}`);
      setOther(c.data);
      setCannotMessage(!c.data.can_message);
      if (chatId) {
        const m = await api.get(`/messages/${chatId}`);
        setMessages(m.data || []);
      }
    } catch (e) {}
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
    // eslint-disable-next-line
  }, [otherId, user]);

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

  const sendGift = async (kind) => {
    try {
      await api.post("/gifts/send", { to_user_id: otherId, gift_kind: kind });
      toast.success("Sovg'a yuborildi");
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Balans yetmaydi");
    }
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
              <img src={other.photo_url} alt="" className={`w-full h-full object-cover ${!other.photo_unlocked ? "blur-md" : ""}`} />
            )}
          </div>
          <div className="min-w-0">
            <p className="font-medium truncate">{other.name}, {other.age}</p>
            <p className="text-xs text-muted-foreground truncate">{other.last_active_label}</p>
          </div>
        </Link>
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
            } ${m.kind === "gift" ? "bg-gold-light text-yellow-900 border-gold/40" : ""} ${m.kind === "super" ? "ring-2 ring-gold" : ""}`}>
              {m.kind === "super" && <span className="text-[9px] uppercase tracking-wider opacity-70 block">Super</span>}
              {m.text}
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

      <div className="fixed bottom-0 inset-x-0 z-40 glass border-t border-border/60 max-w-md mx-auto">
        <div className="p-3">
          {cannotMessage && (
            <div className="mb-2 rounded-2xl bg-gold/10 border border-gold/40 p-3">
              <p className="text-xs">{t("you_dont_pass_filters")}</p>
              <button
                data-testid="send-super"
                onClick={() => send(text || t("greeting_1"), true)}
                className="mt-2 w-full rounded-xl bg-gradient-to-r from-gold to-gold-dark text-white text-sm py-2 font-medium"
              >
                <Sparkles className="w-3 h-3 inline mr-1" /> {t("send_super")}
              </button>
            </div>
          )}
          <div className="flex items-center gap-2">
            <button data-testid="gift-rose" onClick={() => sendGift("rose")} className="p-2.5 rounded-full bg-muted hover:bg-border" title="🌹">
              <Gift className="w-4 h-4" />
            </button>
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
        </div>
      </div>
    </div>
  );
}
