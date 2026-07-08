import React, { useState } from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, Trophy, Medal, Gift } from "lucide-react";
import { useApp } from "@/contexts/AppContext";
import { useLeaderboard } from "@/hooks/queries";
import { photoSrc } from "@/lib/photo";
import { Skeleton, EmptyState } from "@/components/kit";

export default function Rankings() {
  const { t } = useApp();
  const [period, setPeriod] = useState("all");

  const { data: leaders = [], isLoading } = useLeaderboard(period);

  const getRankBadge = (rank) => {
    if (rank === 1) return <Medal className="w-5 h-5 text-yellow-500" />;
    if (rank === 2) return <Medal className="w-5 h-5 text-gray-400" />;
    if (rank === 3) return <Medal className="w-5 h-5 text-amber-700" />;
    return <span className="text-sm font-medium text-muted-foreground">#{rank}</span>;
  };

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 glass border-b border-border/40 px-4 py-3 flex items-center gap-3">
        <Link to="/me" className="p-2 -ml-2 rounded-full hover:bg-muted">
          <ChevronLeft className="w-5 h-5" />
        </Link>
        <span className="font-heading font-bold text-lg flex items-center gap-2"><Trophy className="w-5 h-5 text-gold-dark" /> {t("top_supporters")}</span>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6 space-y-6">
        <div className="flex gap-2 overflow-x-auto pb-2">
          {[
            ["day", t("daily")],
            ["week", t("weekly")],
            ["month", t("monthly")],
            ["all", t("all_time")],
          ].map(([k, l]) => (
            <button
              key={k}
              data-testid={`rankings-period-${k}`}
              onClick={() => setPeriod(k)}
              className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap ${
                period === k ? "bg-primary text-white" : "bg-muted/30 text-muted-foreground"
              }`}
            >
              {l}
            </button>
          ))}
        </div>

        <section className="rounded-3xl border border-border bg-card p-6">
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="flex items-center gap-3 p-3">
                  <Skeleton className="w-8 h-5 rounded-lg" />
                  <Skeleton className="w-10 h-10 rounded-full" />
                  <div className="flex-1 space-y-1.5">
                    <Skeleton className="h-3.5 w-1/2 rounded" />
                    <Skeleton className="h-2.5 w-1/4 rounded" />
                  </div>
                  <Skeleton className="h-4 w-16 rounded" />
                </div>
              ))}
            </div>
          ) : leaders.length === 0 ? (
            <EmptyState icon={<Trophy className="w-6 h-6" />} title={t("no_data")} hint={t("rankings_empty_hint")} />
          ) : (
            <div className="space-y-3">
              {leaders.map((row, i) => {
                const rank = i + 1;
                return (
                  <div
                    key={row.user?.id || i}
                    className={`flex items-center gap-3 p-3 rounded-xl ${
                      rank <= 3 ? "bg-gradient-to-r from-gold/10 to-transparent" : "bg-muted/30"
                    }`}
                  >
                    <div className="w-8 flex justify-center shrink-0">{getRankBadge(rank)}</div>
                    <div className="w-10 h-10 rounded-full bg-muted overflow-hidden shrink-0">
                      {row.user?.photo_url && (
                        <img loading="lazy" decoding="async" src={photoSrc(row.user.photo_url)} alt="" className="w-full h-full object-cover" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{row.user?.name || "—"}</p>
                      <p className="text-xs text-muted-foreground">{row.user?.region}</p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-sm font-semibold">{(row.total || 0).toLocaleString()} {t("sum")}</p>
                      <p className="text-[11px] text-muted-foreground inline-flex items-center gap-1 justify-end"><Gift className="w-3 h-3" /> {row.count || 0}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
