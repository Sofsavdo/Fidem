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
  const [error, setError] = useState(null);

  const load = async () => {
    try {
      const [i, s, l] = await Promise.all([
        api.get("/me/influence").catch(() => ({ data: null })),
        api.get("/me/status").catch(() => ({ data: null })),
        api.get("/me/lifetime-contribution").catch(() => ({ data: null }))
      ]);
      setInfluenceData(i.data);
      setStatusData(s.data);
      setLifetimeData(l.data);
    } catch (e) {
      console.error("Economy load error:", e);
      setError("Failed to load economy data");
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  if (loading) return <div className="p-6 text-muted-foreground">{t("loading")}</div>;
  if (error) return <div className="p-6 text-red-500">{error}</div>;

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 glass border-b border-border/40 px-4 py-3 flex items-center gap-3">
        <Link to="/me" className="p-2 -ml-2 rounded-full hover:bg-muted">
          <ChevronLeft className="w-5 h-5" />
        </Link>
        <span className="font-heading font-bold text-lg">Economy</span>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6 space-y-6">
        {/* Influence Score - Simplified */}
        <section className="rounded-3xl border border-border bg-card p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-2xl bg-primary text-white grid place-items-center">
              <TrendingUp className="w-5 h-5" />
            </div>
            <div className="flex-1">
              <p className="text-xs text-muted-foreground">Reyting balli</p>
              <p className="text-2xl font-heading font-semibold">{(influenceData?.influence_score || 0).toLocaleString()}</p>
            </div>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Status:</span>
            <span className="font-medium capitalize">{statusData?.status || "Bronze"}</span>
          </div>
        </section>

        {/* Simple CTA */}
        <Link
          to="/economy/donations"
          className="block rounded-3xl border-2 border-primary bg-primary/5 p-6 text-center"
        >
          <Gift className="w-8 h-8 mx-auto text-foreground mb-2" />
          <h3 className="font-heading font-semibold">Reytingni oshirish</h3>
          <p className="text-sm text-muted-foreground mt-1">Yuqori reyting = ko'procha ko'rishlar</p>
        </Link>
      </main>
    </div>
  );
}
