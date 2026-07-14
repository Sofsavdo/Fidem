import React from "react";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { toast } from "sonner";
import { Sparkles, Crown, CheckCircle2, Clock, Heart } from "lucide-react";
import { photoSrc } from "@/lib/photo";
import { Link, useNavigate } from "react-router-dom";
import { useConciergeInfo, useConciergeMine, QK } from "@/hooks/queries";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { openExternalLink } from "@/lib/telegram";

export default function Concierge() {
  const { t } = useApp();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: info } = useConciergeInfo();
  const { data: orders = [] } = useConciergeMine();

  const orderMutation = useMutation({
    mutationFn: (method) => api.post("/concierge/order", { payment_method: method }),
    onSuccess: (r) => {
      if (r.data.payment_link) {
        toast.info(t("redirecting_payment"));
        setTimeout(() => { openExternalLink(r.data.payment_link); }, 600);
      } else {
        toast.success("🎉 " + t("order_concierge"));
      }
      queryClient.invalidateQueries({ queryKey: QK.conciergeInfo });
      queryClient.invalidateQueries({ queryKey: QK.conciergeMine });
    },
    onError: (e) => {
      const detail = (e?.response?.data?.detail || "").toString();
      if (detail === "click_disabled") {
        toast.info(t("click_disabled_error"));
        navigate("/premium?tab=balance");
      } else {
        toast.error(detail || t("error_generic"));
      }
    },
  });

  const order = (method) => orderMutation.mutate(method);
  const loading = orderMutation.isPending;

  const statusLabel = (s) => ({
    awaiting_payment: t("concierge_status_awaiting_payment"),
    in_progress: t("concierge_status_in_progress"),
    active: "Active",
    completed: t("concierge_status_completed"),
    expired: "—",
  })[s] || s;

  if (!info) return <div className="p-6 text-muted-foreground">{t("loading_word")}</div>;

  return (
    <div className="max-w-3xl mx-auto p-4 md:p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-heading font-semibold flex items-center gap-2">
          <Sparkles className="w-6 h-6 text-secondary" /> {t("concierge_title")}
        </h1>
        <p className="text-sm text-muted-foreground mt-1">{t("concierge_desc")}</p>
      </div>

      {/* Pricing card */}
      <div className="rounded-3xl bg-gradient-to-br from-primary/15 via-secondary/10 to-gold-light/20 border border-border p-6 space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <div className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-secondary text-white">
              <Crown className="w-3 h-3" /> PREMIUM
            </div>
            <h2 className="text-3xl font-heading font-semibold mt-2">{info.price.toLocaleString()} {t("sum_word")}</h2>
            <p className="text-sm text-muted-foreground">{info.days} {t("day_word")} · {info.max_matches} matches</p>
          </div>
          <Heart className="w-10 h-10 text-primary/30" fill="currentColor" />
        </div>
        <ul className="text-sm space-y-2">
          <li className="flex gap-2"><CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" /> {t("concierge_desc")}</li>
          <li className="flex gap-2"><CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" /> {info.max_matches} × hand-picked</li>
          <li className="flex gap-2"><CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" /> Personalized review</li>
        </ul>
        {!info.active_order && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <button data-testid="concierge-click" onClick={() => order("click")} disabled={loading} className="py-3 rounded-2xl bg-primary text-white font-medium disabled:opacity-50">
              {t("activate_with_click")}
            </button>
            <button data-testid="concierge-balance" onClick={() => order("balance")} disabled={loading || !info.can_balance_pay} className="py-3 rounded-2xl border-2 border-primary text-foreground font-medium disabled:opacity-30">
              {t("activate_with_balance")} {info.can_balance_pay ? "✓" : "✗"}
            </button>
          </div>
        )}
      </div>

      {/* Active order */}
      {orders.length > 0 && (
        <div className="space-y-4">
          <h2 className="font-semibold">{t("your_orders")}</h2>
          {orders.map((o) => (
            <div key={o.id} className="rounded-3xl border border-border bg-card p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm"><span className="font-medium">{o.amount.toLocaleString()} {t("sum_word")}</span> · {new Date(o.created_at).toLocaleDateString()}</p>
                  <p className="text-xs text-muted-foreground">{statusLabel(o.status)}</p>
                </div>
                <span className="text-xs font-medium">{(o.matches || []).length}/{info.max_matches}</span>
              </div>
              {(o.match_users || []).length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {o.match_users.map((m) => (
                    <Link key={m.id} to={`/candidate/${m.id}`} className="flex items-center gap-3 p-3 rounded-xl bg-muted/40 hover:bg-muted transition">
                      <div className="w-12 h-12 rounded-xl bg-muted overflow-hidden">
                        {m.photo_url && <img loading="lazy" decoding="async" src={photoSrc(m.photo_url)} alt="" className="w-full h-full object-cover" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium">{m.name}, {m.age}</p>
                        <p className="text-xs text-muted-foreground truncate">{m.region} · {m.profession}</p>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : o.status === "in_progress" ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Clock className="w-4 h-4" /> {t("concierge_status_in_progress")}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
