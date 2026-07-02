import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, TrendingUp, Crown, Gift, Heart, Coins, Zap, Info } from "lucide-react";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";

export default function Economy() {
  const { t } = useApp();
  const [influenceData, setInfluenceData] = useState(null);
  const [statusData, setStatusData] = useState(null);
  const [lifetimeData, setLifetimeData] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const [i, s, l] = await Promise.all([
        api.get("/me/influence"),
        api.get("/me/status"),
        api.get("/me/lifetime-contribution")
      ]);
      setInfluenceData(i.data);
      setStatusData(s.data);
      setLifetimeData(l.data);
    } catch {/* ignore */}
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  if (loading) return <div className="p-6 text-muted-foreground">{t("loading")}</div>;

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 glass border-b border-border/40 px-4 py-3 flex items-center gap-3">
        <Link to="/me" className="p-2 -ml-2 rounded-full hover:bg-muted">
          <ChevronLeft className="w-5 h-5" />
        </Link>
        <span className="font-heading font-bold text-lg">Economy</span>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6 space-y-6">
        {/* Influence Score */}
        <section className="rounded-3xl border border-border bg-card p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-2xl bg-primary text-white grid place-items-center">
              <TrendingUp className="w-5 h-5" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <p className="text-xs text-muted-foreground">{t("economy_what")}</p>
                <Info className="w-3 h-3 text-muted-foreground cursor-help" title={t("economy_why") + " • " + t("economy_benefit_1")} />
              </div>
              <p className="text-2xl font-heading font-semibold">{(influenceData?.influence_score || 0).toLocaleString()}</p>
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">{t("economy_status")}</span>
              <span className="font-medium capitalize">{statusData?.status || "Bronze"}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">{t("economy_badges")}</span>
              <span className="font-medium">{statusData?.badges?.join(", ") || t("economy_none")}</span>
            </div>
          </div>
        </section>

        {/* Status Ladder */}
        <section className="rounded-3xl border border-border bg-card p-6">
          <h2 className="font-heading font-semibold mb-4 flex items-center gap-2">
            <Crown className="w-5 h-5 text-gold-dark" /> {t("economy_status_ladder")}
          </h2>
          <div className="space-y-3">
            {[
              { name: "Bronze", threshold: 0 },
              { name: "Silver", threshold: 1000 },
              { name: "Gold", threshold: 5000 },
              { name: "Platinum", threshold: 15000 },
              { name: "Diamond", threshold: 50000 },
              { name: "Legend", threshold: 150000 },
            ].map((s) => (
              <div
                key={s.name}
                className={`flex items-center justify-between p-3 rounded-xl ${
                  statusData?.status?.toLowerCase() === s.name.toLowerCase()
                    ? "bg-primary/10 border-2 border-primary"
                    : "bg-muted/30"
                }`}
              >
                <span className="font-medium">{s.name}</span>
                <span className="text-sm text-muted-foreground">{s.threshold.toLocaleString()} pts</span>
              </div>
            ))}
          </div>
        </section>

        {/* Lifetime Contribution */}
        <section className="rounded-3xl border border-border bg-card p-6">
          <h2 className="font-heading font-semibold mb-4 flex items-center gap-2">
            <Heart className="w-5 h-5 text-rose-500" /> {t("economy_lifetime")}
          </h2>
          <div className="text-center mb-4">
            <p className="text-3xl font-heading font-bold">{(lifetimeData?.lifetime_contribution || 0).toLocaleString()}</p>
            <p className="text-sm text-muted-foreground">{t("economy_total_contributed")}</p>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="rounded-xl bg-muted/30 p-3">
              <p className="text-muted-foreground">{t("economy_balance_spent")}</p>
              <p className="font-medium">{(lifetimeData?.breakdown?.balance_spent || 0).toLocaleString()}</p>
            </div>
            <div className="rounded-xl bg-muted/30 p-3">
              <p className="text-muted-foreground">{t("economy_donations")}</p>
              <p className="font-medium">{(lifetimeData?.breakdown?.donations_converted || 0).toLocaleString()}</p>
            </div>
            <div className="rounded-xl bg-muted/30 p-3">
              <p className="text-muted-foreground">{t("economy_referral_earnings")}</p>
              <p className="font-medium">{(lifetimeData?.breakdown?.referral_earnings_converted || 0).toLocaleString()}</p>
            </div>
            <div className="rounded-xl bg-muted/30 p-3">
              <p className="text-muted-foreground">{t("economy_subscriptions")}</p>
              <p className="font-medium">{(lifetimeData?.breakdown?.subscription_payments || 0).toLocaleString()}</p>
            </div>
          </div>
        </section>

        {/* Donation CTA */}
        <Link
          to="/economy/donations"
          className="block rounded-3xl border-2 border-primary bg-primary/5 p-6 text-center"
        >
          <Gift className="w-8 h-8 mx-auto text-primary mb-2" />
          <h3 className="font-heading font-semibold">Convert to Influence</h3>
          <p className="text-sm text-muted-foreground mt-1">Higher influence = higher rankings = more visibility</p>
        </Link>
      </main>
    </div>
  );
}
