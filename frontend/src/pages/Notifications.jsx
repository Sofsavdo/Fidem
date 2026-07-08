import React, { useEffect } from "react";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Bell, Eye, Heart, Gift, MessageCircle, ShieldCheck, Trophy, Sparkles } from "lucide-react";
import { useNotifications } from "@/hooks/queries";
import { useQueryClient } from "@tanstack/react-query";
import { QK } from "@/hooks/queries";

const ICONS = {
  view: Eye, saved: Heart, gift: Gift, message: MessageCircle, photo_request: ShieldCheck,
  photo_grant: ShieldCheck, match: Sparkles, premium: Trophy, balance: Trophy, marketing: Bell,
  referral: Trophy, verified: ShieldCheck,
};

export default function Notifications() {
  const { t } = useApp();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: items = [], isLoading } = useNotifications();

  useEffect(() => {
    api.post("/notifications/read-all")
      .then(() => queryClient.invalidateQueries({ queryKey: QK.notifications }))
      .catch(() => {});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const openLink = (link) => {
    if (!link) return;
    if (link.startsWith("http://") || link.startsWith("https://")) {
      try {
        const u = new URL(link);
        navigate(u.pathname + u.search);
      } catch {
        window.location.href = link;
      }
      return;
    }
    navigate(link);
  };

  return (
    <div className="px-4 pt-6 pb-8" data-testid="notifications-page">
      <div className="flex items-center gap-3 mb-4">
        <Link to="/me" className="p-2 rounded-full hover:bg-muted" data-testid="notif-back">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <h1 className="font-heading text-2xl font-semibold tracking-tight">{t("notifications")}</h1>
      </div>

      {isLoading && <div className="text-center py-6 text-muted-foreground">{t("loading")}</div>}
      {!isLoading && items.length === 0 && <div className="text-center py-12 text-muted-foreground">{t("no_data")}</div>}

      <div className="space-y-2">
        {items.map((n) => {
          const Icon = ICONS[n.kind] || Bell;
          const clickable = Boolean(n.link);
          return (
            <div
              key={n.id}
              data-testid={`notif-${n.id}`}
              role={clickable ? "button" : undefined}
              tabIndex={clickable ? 0 : undefined}
              onClick={() => openLink(n.link)}
              onKeyDown={(e) => {
                if (clickable && (e.key === "Enter" || e.key === " ")) {
                  e.preventDefault();
                  openLink(n.link);
                }
              }}
              className={`rounded-2xl border border-border p-3 flex items-start gap-3 ${n.read ? "bg-card" : "bg-muted/40"} ${clickable ? "cursor-pointer hover:bg-muted/50 transition-colors" : ""}`}
            >
              <div className="w-9 h-9 rounded-full bg-muted grid place-items-center flex-shrink-0">
                <Icon className="w-4 h-4 text-foreground" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm">{n.text}</p>
                <p className="text-[11px] text-muted-foreground mt-0.5">{n.created_at ? new Date(n.created_at).toLocaleString() : "—"}</p>
              </div>
              {!n.read && <span className="w-1.5 h-1.5 rounded-full bg-primary mt-2" />}
            </div>
          );
        })}
      </div>
    </div>
  );
}
