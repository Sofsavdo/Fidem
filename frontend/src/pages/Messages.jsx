import React, { useState } from "react";
import { Link } from "react-router-dom";
import { MessageCircle, Inbox, Sparkles } from "lucide-react";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { photoSrc } from "@/lib/photo";
import { useMessagesChats, useMessagesApplications, QK } from "@/hooks/queries";
import { useQueryClient } from "@tanstack/react-query";
import { EmptyState, Skeleton } from "@/components/kit";

export default function Messages() {
  const { t } = useApp();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState("chats");

  const { data: chats = [], isLoading: loadingChats } = useMessagesChats();
  const { data: apps = [], isLoading: loadingApps } = useMessagesApplications();
  const loading = loadingChats || loadingApps;

  const reload = () => {
    queryClient.invalidateQueries({ queryKey: QK.messagesChats });
    queryClient.invalidateQueries({ queryKey: QK.messagesApplications });
  };

  // Refresh chats when a match happens
  React.useEffect(() => {
    const handleMatch = () => {
      reload();
    };
    window.addEventListener("fidem:match", handleMatch);
    return () => window.removeEventListener("fidem:match", handleMatch);
  }, [queryClient]);

  const matches = chats.filter((c) => c.status === "match");

  return (
    <div className="px-4 md:px-8 pt-6">
      <h1 className="font-heading text-3xl md:text-4xl font-semibold tracking-tight mb-4">{t("messages")}</h1>
      <div className="flex gap-2 mb-4 border-b border-border">
        {[
          { k: "chats", l: t("chats") },
          { k: "applications", l: t("applications") + (apps.length ? ` (${apps.length})` : "") },
          { k: "matches", l: t("matches") },
        ].map((x) => (
          <button
            key={x.k}
            data-testid={`tab-${x.k}`}
            onClick={() => setTab(x.k)}
            className={`pb-2 px-1 text-sm border-b-2 -mb-px ${
              tab === x.k ? "border-primary text-foreground font-medium" : "border-transparent text-muted-foreground"
            }`}
          >
            {x.l}
          </button>
        ))}
      </div>

      {loading && (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3 bg-card rounded-2xl p-3 border border-border">
              <Skeleton className="w-12 h-12 rounded-full" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-3.5 w-1/3 rounded" />
                <Skeleton className="h-2.5 w-2/3 rounded" />
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === "chats" && !loading && (
        <div className="space-y-2" data-testid="chat-list">
          {chats.length === 0 ? (
            <EmptyState icon={<MessageCircle className="w-6 h-6" />} title={t("messages_empty_title")} hint={t("messages_empty_hint")}
              action={<Link to="/" className="text-sm font-semibold text-primary">{t("candidates")} →</Link>} />
          ) : chats.map((c) => <ChatRowMemo key={c.chat_id} c={c} />)}
        </div>
      )}
      {tab === "applications" && !loading && (
        <div className="space-y-2" data-testid="app-list">
          {apps.length === 0 ? (
            <EmptyState icon={<Inbox className="w-6 h-6" />} title={t("applications_empty_title")} hint={t("applications_empty_hint")} />
          ) : apps.map((a) => <ApplicationRowMemo key={a.application.id} a={a} onChange={reload} />)}
        </div>
      )}
      {tab === "matches" && !loading && (
        <div className="space-y-2" data-testid="matches-list">
          {matches.length === 0 ? (
            <EmptyState icon={<Sparkles className="w-6 h-6" />} title={t("matches_empty_title")} hint={t("matches_empty_hint")} />
          ) : matches.map((c) => <ChatRowMemo key={c.chat_id} c={c} />)}
        </div>
      )}
    </div>
  );
}

function Avatar({ user }) {
  return (
    <div className="relative w-12 h-12 rounded-full overflow-hidden bg-muted flex-shrink-0">
      {user.photo_url ? (
        <img loading="lazy" decoding="async" src={photoSrc(user.photo_url)} alt="" className={`w-full h-full object-cover ${!user.photo_unlocked ? "blur-md" : ""}`} />
      ) : (
        <div className="w-full h-full grid place-items-center text-muted-foreground text-sm">
          {user.name?.[0]}
        </div>
      )}
    </div>
  );
}

const AvatarMemo = React.memo(Avatar);

function ChatRow({ c }) {
  return (
    <Link
      to={`/chat/${c.other.id}`}
      data-testid={`chat-row-${c.other.id}`}
      className="flex items-center gap-3 bg-card rounded-2xl p-3 border border-border hover:shadow-soft transition"
    >
      <AvatarMemo user={c.other} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <p className="font-medium truncate">{c.other.name}</p>
          {c.unread > 0 && <span className="text-[10px] bg-primary text-white px-1.5 py-0.5 rounded-full">{c.unread}</span>}
        </div>
        <p className="text-sm text-muted-foreground truncate">{c.last_message?.text || "..."}</p>
      </div>
    </Link>
  );
}

const ChatRowMemo = React.memo(ChatRow);

function ApplicationRow({ a, onChange }) {
  const { t } = useApp();
  const decide = async (approve) => {
    await api.post(`/messages/applications/${a.application.id}/decide`, { approve });
    onChange();
  };
  return (
    <div className="bg-card rounded-2xl p-3 border border-border" data-testid={`app-row-${a.application.id}`}>
      <div className="flex items-center gap-3">
        <AvatarMemo user={a.from_user} />
        <div className="flex-1 min-w-0">
          <p className="font-medium">{a.from_user.name}, {a.from_user.age}</p>
          <p className="text-xs text-muted-foreground">{a.from_user.region}</p>
        </div>
      </div>
      <p className="mt-2 text-sm">{a.application.text}</p>
      <div className="flex gap-2 mt-2">
        <button data-testid={`app-approve-${a.application.id}`} onClick={() => decide(true)} className="flex-1 rounded-xl bg-secondary text-white text-sm py-2 font-medium active:scale-[0.98] transition">{t("approve")}</button>
        <button data-testid={`app-reject-${a.application.id}`} onClick={() => decide(false)} className="flex-1 rounded-xl border border-border text-sm py-2 font-medium active:scale-[0.98] transition">{t("reject")}</button>
      </div>
    </div>
  );
}

const ApplicationRowMemo = React.memo(ApplicationRow);
