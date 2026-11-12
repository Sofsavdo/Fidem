// Chat extras: day dividers, typing dots, reactions, reply quote, openers,
// the question deck and the assistant's quick questions.
import React from "react";
import { X, Reply, Lightbulb } from "lucide-react";
import { useApp } from "@/contexts/AppContext";
import { photoSrc } from "@/lib/photo";
import { QUESTION_DECK, openersFor, ASSISTANT_CHIPS } from "@/lib/chatQuestions";

export const REACTIONS = ["❤️", "😂", "😮", "👍", "🤲", "😢"];

const sameDay = (a, b) => a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();

export function dayLabel(iso, t, lang) {
  const d = new Date(iso);
  if (isNaN(d)) return "";
  const now = new Date();
  const yest = new Date(now);
  yest.setDate(now.getDate() - 1);
  if (sameDay(d, now)) return t("chat_today");
  if (sameDay(d, yest)) return t("chat_yesterday");
  const loc = lang === "ru" ? "ru-RU" : lang === "en" ? "en-GB" : "uz-UZ";
  try {
    return d.toLocaleDateString(loc, { day: "numeric", month: "long", ...(d.getFullYear() !== now.getFullYear() ? { year: "numeric" } : {}) });
  } catch {
    return d.toDateString();
  }
}

export function isNewDay(prev, cur) {
  if (!prev) return true;
  return !sameDay(new Date(prev.created_at), new Date(cur.created_at));
}

export function DayDivider({ label }) {
  return (
    <div className="self-center my-2 text-[11px] font-medium text-muted-foreground bg-muted/70 rounded-full px-3 py-0.5" data-testid="day-divider">
      {label}
    </div>
  );
}

export function TypingBubble() {
  return (
    <div className="self-start rounded-2xl rounded-bl-sm bg-card border border-border px-3.5 py-2.5 inline-flex gap-1" data-testid="typing-bubble">
      {[0, 1, 2].map((i) => (
        <span key={i} className="w-1.5 h-1.5 rounded-full bg-muted-foreground/70 animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
      ))}
    </div>
  );
}

export function ReactionChips({ reactions, mine, onToggle, myId }) {
  const entries = Object.entries(reactions || {});
  if (!entries.length) return null;
  const counts = {};
  entries.forEach(([, e]) => { counts[e] = (counts[e] || 0) + 1; });
  return (
    <div className={`flex gap-1 -mt-1.5 ${mine ? "justify-end pr-2" : "pl-2"}`} data-testid="msg-reactions">
      {Object.entries(counts).map(([e, n]) => (
        <button key={e} onClick={() => onToggle(e)}
          className={`text-xs rounded-full px-1.5 py-0.5 border shadow-sm bg-card ${reactions?.[myId] === e ? "border-primary" : "border-border"}`}>
          {e}{n > 1 ? ` ${n}` : ""}
        </button>
      ))}
    </div>
  );
}

export function ActionBar({ mine, onReact, onReply, current }) {
  const { t } = useApp();
  return (
    <div className={`flex items-center gap-1 rounded-full bg-card border border-border shadow-elevated px-1.5 py-1 ${mine ? "self-end" : "self-start"}`} data-testid="msg-actions">
      {REACTIONS.map((e) => (
        <button key={e} onClick={() => onReact(e)} className={`text-lg leading-none px-1 rounded-full transition active:scale-125 ${current === e ? "bg-primary/15" : ""}`} aria-label={e}>{e}</button>
      ))}
      <span className="w-px h-5 bg-border mx-0.5" />
      <button onClick={onReply} className="text-xs font-medium px-2 py-1 rounded-full hover:bg-muted inline-flex items-center gap-1" data-testid="msg-reply">
        <Reply className="w-3.5 h-3.5" /> {t("chat_reply")}
      </button>
    </div>
  );
}

export function QuotedMessage({ q, mine, myId, otherName }) {
  const { t } = useApp();
  if (!q) return null;
  const who = q.from_user_id === myId ? t("chat_you") : otherName;
  return (
    <div className={`mb-1.5 rounded-lg px-2 py-1 border-l-2 text-xs ${mine ? "bg-white/15 border-white/70" : "bg-muted border-primary"}`} data-testid="msg-quote">
      <p className="font-semibold opacity-90">{who}</p>
      <p className="opacity-80 line-clamp-2">{q.kind === "voice" ? "🎙" : q.text}</p>
    </div>
  );
}

export function ReplyPreview({ msg, myId, otherName, onCancel }) {
  const { t } = useApp();
  if (!msg) return null;
  return (
    <div className="flex items-center gap-2 rounded-2xl bg-card border border-border px-3 py-2" data-testid="reply-preview">
      <Reply className="w-4 h-4 text-primary shrink-0" />
      <div className="min-w-0 flex-1 border-l-2 border-primary pl-2">
        <p className="text-[11px] font-semibold text-primary">{msg.from_user_id === myId ? t("chat_you") : otherName}</p>
        <p className="text-xs text-muted-foreground truncate">{msg.kind === "voice" ? "🎙" : msg.text}</p>
      </div>
      <button onClick={onCancel} className="p-1 rounded-full hover:bg-muted" aria-label="cancel"><X className="w-3.5 h-3.5" /></button>
    </div>
  );
}

// Empty chat: who this is, why you match, and three ready first messages.
export function Openers({ other, onPick }) {
  const { t, user, lang } = useApp();
  const openers = openersFor(other, user, lang);
  const facts = [other.region, other.profession, other.education].filter(Boolean).slice(0, 3);
  return (
    <div className="self-stretch rounded-3xl border border-border bg-card p-4 space-y-3 shadow-soft" data-testid="chat-openers">
      <div className="flex items-center gap-3">
        <div className="w-14 h-14 rounded-2xl overflow-hidden bg-muted shrink-0">
          {other.photo_url && <img src={photoSrc(other.photo_url)} alt="" className="w-full h-full object-cover" />}
        </div>
        <div className="min-w-0">
          <p className="font-heading text-lg font-semibold leading-tight">{other.name}, {other.age}</p>
          <p className="text-xs text-muted-foreground truncate">{facts.join(" · ")}</p>
          {other.match_score != null && <p className="text-xs text-primary font-semibold mt-0.5">💞 {t("chat_match").replace("{n}", other.match_score)}</p>}
        </div>
      </div>
      <p className="text-xs font-medium text-muted-foreground">✍️ {t("chat_openers_title")}</p>
      <div className="space-y-1.5">
        {openers.map((o, i) => (
          <button key={i} onClick={() => onPick(o)} data-testid={`opener-${i}`}
            className="w-full text-left text-sm rounded-2xl border border-primary/30 bg-primary/5 px-3 py-2 hover:bg-primary/10 active:scale-[0.99] transition">
            {o}
          </button>
        ))}
      </div>
    </div>
  );
}

export function AssistantChips({ onPick }) {
  const { lang } = useApp();
  const chips = ASSISTANT_CHIPS[lang] || ASSISTANT_CHIPS.uz;
  return (
    <div className="flex gap-1.5 overflow-x-auto no-scrollbar pb-0.5" data-testid="assistant-chips">
      {chips.map((c) => (
        <button key={c} onClick={() => onPick(c)} className="shrink-0 text-xs rounded-full border border-violet-300 dark:border-violet-800 bg-violet-50 dark:bg-violet-950/40 px-3 py-1.5">
          {c}
        </button>
      ))}
    </div>
  );
}

export function QuestionDeckButton({ onClick, disabled }) {
  const { t } = useApp();
  return (
    <button data-testid="question-deck-open" onClick={onClick} disabled={disabled} title={t("chat_deck_title")}
      className="shrink-0 w-10 h-10 grid place-items-center rounded-full bg-amber-100 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300 hover:brightness-95 disabled:opacity-40">
      <Lightbulb className="w-4 h-4" />
    </button>
  );
}

export function QuestionDeck({ open, onClose, onPick }) {
  const { t, lang } = useApp();
  const deck = QUESTION_DECK[lang] || QUESTION_DECK.uz;
  const cats = Object.keys(deck);
  const [cat, setCat] = React.useState(cats[0]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 flex items-end" style={{ zIndex: 10001 }} data-testid="question-deck">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative w-full max-w-md mx-auto bg-card rounded-t-3xl p-4 space-y-3 max-h-[75vh] overflow-y-auto"
        style={{ paddingBottom: "max(1rem, env(safe-area-inset-bottom))" }}>
        <div className="flex items-center justify-between">
          <h3 className="font-heading text-lg font-semibold">💡 {t("chat_deck_title")}</h3>
          <button onClick={onClose} className="p-2 rounded-full hover:bg-muted"><X className="w-4 h-4" /></button>
        </div>
        <p className="text-xs text-muted-foreground">{t("chat_deck_hint")}</p>
        <div className="flex gap-1.5 overflow-x-auto no-scrollbar">
          {cats.map((c) => (
            <button key={c} onClick={() => setCat(c)}
              className={`shrink-0 text-xs rounded-full px-3 py-1.5 border ${c === cat ? "bg-foreground text-background border-foreground" : "bg-card border-border"}`}>{c}</button>
          ))}
        </div>
        <div className="space-y-1.5">
          {deck[cat].map((q) => (
            <button key={q} onClick={() => onPick(q)} className="w-full text-left text-sm rounded-2xl border border-border px-3 py-2.5 hover:bg-muted active:scale-[0.99] transition">
              {q}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
