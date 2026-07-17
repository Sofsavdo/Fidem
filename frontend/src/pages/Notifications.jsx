import React, { useEffect } from "react";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Bell, Eye, Heart, Gift, MessageCircle, ShieldCheck, Trophy, Sparkles } from "lucide-react";
import { useNotifications } from "@/hooks/queries";
import { useQueryClient } from "@tanstack/react-query";
import { QK } from "@/hooks/queries";
import { Skeleton, EmptyState } from "@/components/kit";
import { localeFor } from "@/lib/time";

const ICONS = {
  view: Eye, saved: Heart, gift: Gift, message: MessageCircle, photo_request: ShieldCheck,
  photo_grant: ShieldCheck, match: Sparkles, premium: Trophy, balance: Trophy, marketing: Bell,
  referral: Trophy, verified: ShieldCheck,
};

export default function Notifications() {
  const { t, lang } = useApp();
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

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="rounded-2xl border border-border p-3 flex items-start gap-3">
              <Skeleton className="w-9 h-9 rounded-full" />
              <div className="flex-1 space-y-1.5">
                <Skeleton className="h-3.5 w-3/4 rounded" />
                <Skeleton className="h-2.5 w-1/3 rounded" />
              </div>
            </div>
          ))}
        </div>
      )}
      {!isLoading && items.length === 0 && (
        <EmptyState icon={<Bell className="w-6 h-6" />} title={t("no_data")} hint={t("notifications_empty_hint")} />
      )}

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
                <p className="text-[11px] text-muted-foreground mt-0.5">{n.created_at ? new Date(n.created_at).toLocaleString(localeFor(lang)) : "—"}</p>
              </div>
              {!n.read && <span className="w-1.5 h-1.5 rounded-full bg-primary mt-2" />}
            </div>
          );
        })}
      </div>
    </div>
  );
}
