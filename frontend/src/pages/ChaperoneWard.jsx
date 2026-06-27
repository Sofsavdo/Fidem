import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "@/lib/api";
import { ArrowLeft, Eye } from "lucide-react";
import { photoSrc } from "@/lib/photo";

export default function ChaperoneWard() {
  const { wardId } = useParams();
  const [chats, setChats] = useState([]);
  const [active, setActive] = useState(null);
  const [messages, setMessages] = useState([]);

  useEffect(() => {
    api.get(`/chaperone/ward/${wardId}/chats`).then((r) => setChats(r.data || [])).catch(() => {});
  }, [wardId]);

  const openChat = async (chatId) => {
    setActive(chatId);
    const r = await api.get(`/chaperone/ward/${wardId}/messages/${chatId}`);
    setMessages(r.data || []);
  };

  return (
    <div className="p-5 max-w-4xl mx-auto pb-24" data-testid="chaperone-ward">
      <Link to="/chaperone" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-3">
        <ArrowLeft className="w-4 h-4" /> Orqaga
      </Link>
      <div className="flex items-center gap-2 mb-4">
        <Eye className="w-5 h-5 text-secondary" />
        <h1 className="font-heading text-xl font-semibold">Faqat kuzatish rejimi</h1>
      </div>
      <p className="text-xs text-muted-foreground mb-5">Bu yerda ward'ingizning suhbatlarini xolisona kuzatishingiz mumkin. Siz yoza olmaysiz.</p>

      <div className="grid md:grid-cols-3 gap-4">
        <div className="space-y-2">
          {chats.length === 0 && <p className="text-sm text-muted-foreground">Suhbatlar yo'q</p>}
          {chats.map((c) => (
            <button
              key={c.chat_id}
              onClick={() => openChat(c.chat_id)}
              className={`w-full rounded-2xl bg-card border p-3 text-left flex items-center gap-3 ${active === c.chat_id ? "border-primary" : "border-border"}`}
            >
              <div className="w-10 h-10 rounded-xl bg-muted overflow-hidden">
                {c.other.photo_url && <img src={photoSrc(c.other.photo_url)} alt="" className="w-full h-full object-cover" />}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{c.other.name}</p>
                <p className="text-xs text-muted-foreground truncate">{c.last_text || "…"}</p>
              </div>
            </button>
          ))}
        </div>
        <div className="md:col-span-2 rounded-2xl bg-card border border-border p-4 min-h-[300px]">
          {!active && <p className="text-sm text-muted-foreground text-center pt-12">Chat tanlang</p>}
          {active && (
            <div className="space-y-2">
              {messages.map((m) => (
                <div key={m.id} className="text-sm border-b border-border/40 pb-2">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                    {m.from_user_id === wardId ? "Ward" : "Boshqa"} · {m.kind}
                  </p>
                  <p>{m.text}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
