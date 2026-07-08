import React, { useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { photoSrc } from "@/lib/photo";
import { useMessagesChats, useMessagesApplications, QK } from "@/hooks/queries";
import { useQueryClient } from "@tanstack/react-query";

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

      {loading ? <div className="text-muted-foreground py-6 text-center">{t("loading")}</div> : null}

      {tab === "chats" && (
        <div className="space-y-2" data-testid="chat-list">
          {chats.length === 0 && !loading && <Empty label={t("no_data")} />}
          {chats.map((c) => <ChatRowMemo key={c.chat_id} c={c} />)}
        </div>
      )}
      {tab === "applications" && (
        <div className="space-y-2" data-testid="app-list">
          {apps.length === 0 && !loading && <Empty label={t("no_data")} />}
          {apps.map((a) => <ApplicationRowMemo key={a.application.id} a={a} onChange={reload} />)}
        </div>
      )}
      {tab === "matches" && (
        <div className="space-y-2" data-testid="matches-list">
          {matches.length === 0 && !loading && <Empty label={t("no_data")} />}
          {matches.map((c) => <ChatRowMemo key={c.chat_id} c={c} />)}
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
        <button data-testid={`app-approve-${a.application.id}`} onClick={() => decide(true)} className="flex-1 rounded-xl bg-secondary text-white text-sm py-2">Qabul</button>
        <button data-testid={`app-reject-${a.application.id}`} onClick={() => decide(false)} className="flex-1 rounded-xl border border-border text-sm py-2">Rad</button>
      </div>
    </div>
  );
}

const ApplicationRowMemo = React.memo(ApplicationRow);

function Empty({ label }) {
  return <div className="py-16 text-center text-muted-foreground" data-testid="empty">{label}</div>;
}
