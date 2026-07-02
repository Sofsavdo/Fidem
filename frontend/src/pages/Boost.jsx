import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { ArrowLeft, Sparkles, Star, Rocket, Eye, Heart, MessageSquare, Trophy, Activity } from "lucide-react";
import { toast } from "sonner";
import { photoSrc } from "@/lib/photo";

export default function Boost() {
  const { t, user, refresh } = useApp();
  const [status, setStatus] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [busy, setBusy] = useState(false);

  const load = () => Promise.all([
    api.get("/boost/status").then((r) => setStatus(r.data)),
    api.get("/boost/analytics").then((r) => setAnalytics(r.data)).catch(() => {}),
    api.get("/rankings/global").then((r) => setLeaderboard(r.data?.rankings || [])).catch(() => {}),
  ]);
  useEffect(() => { load(); }, []);

  const activate = async (kind) => {
    setBusy(true);
    try {
      const r = await api.post(`/${kind}/activate`, { use_balance: true });
      toast.success(kind === "boost" ? t("profile_boost_title") + " ✅" : t("spotlight_title") + " ✅");
      await refresh();
      load();
    } catch (e) {
      const msg = e.response?.data?.detail;
      if (msg && msg.includes("Need")) {
        toast.error(`${msg} — balansni to'ldiring`);
      } else {
        toast.error(msg || "Xato");
      }
    } finally {
      setBusy(false);
    }
  };

  const payViaClick = async (purpose, amount) => {
    try {
      const r = await api.post("/payments/create", { purpose: "balance_topup", amount });
      window.open(r.data.payment_link, "_blank");
      toast.success("To'lov sahifasi ochildi — to'lovdan keyin balansni avto-yangilaymiz");
    } catch (e) {
      toast.error("Xato");
    }
  };

  return (
    <div className="px-4 md:px-8 pt-6 pb-8 space-y-5" data-testid="boost-page">
      <div className="flex items-center gap-3">
        <Link to="/me" className="p-2 rounded-full hover:bg-muted" data-testid="boost-back">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div>
          <h1 className="font-heading text-2xl md:text-3xl font-semibold tracking-tight">{t("boost_title")}</h1>
          <p className="text-xs text-muted-foreground">{t("boost_subtitle")}</p>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        {/* Boost */}
        <div className="rounded-3xl border-2 border-primary/30 bg-gradient-to-br from-primary/5 to-card p-5" data-testid="card-boost">
          <div className="flex items-center justify-between">
            <Rocket className="w-7 h-7 text-foreground" />
            <span className="text-xs px-2 py-1 rounded-full bg-primary/10 text-foreground font-medium">24 {t("hour_word").toUpperCase()}</span>
          </div>
          <h2 className="font-heading text-2xl font-semibold mt-3">{t("profile_boost_title")}</h2>
          <p className="text-sm text-muted-foreground mt-1">{t("profile_boost_desc")}</p>
          <ul className="text-sm mt-3 space-y-1">
            <li>✓ {t("bullet_top_feed")}</li>
            <li>✓ {t("bullet_views_3_5x")}</li>
            <li>✓ {t("bullet_faster_messages")}</li>
          </ul>
          <p className="font-heading text-xl mt-4">5,000 {t("sum_word")}</p>
          {status?.active && (
            <p className="text-xs text-secondary mt-2">{t("travel_active")} — {new Date(status.until).toLocaleString()}</p>
          )}
          <div className="flex flex-col sm:flex-row gap-2 mt-3">
            <button
              data-testid="buy-boost-balance"
              onClick={() => activate("boost")}
              disabled={busy || status?.active}
              className="flex-1 rounded-2xl bg-primary text-white py-3 font-medium disabled:opacity-50"
            >
              {t("activate_with_balance")} ({(user?.balance || 0).toLocaleString()})
            </button>
            <button
              data-testid="buy-boost-click"
              onClick={() => payViaClick("boost", 5000)}
              className="flex-1 rounded-2xl border border-border bg-card py-3 font-medium hover:bg-muted"
            >
              CLICK
            </button>
          </div>
        </div>

        {/* Spotlight */}
        <div className="rounded-3xl border-2 border-gold/40 bg-gradient-to-br from-gold-light/30 to-card p-5" data-testid="card-spotlight">
          <div className="flex items-center justify-between">
            <Star className="w-7 h-7 text-gold-dark" fill="currentColor" />
            <span className="text-xs px-2 py-1 rounded-full bg-gold-light text-yellow-900 font-medium">7 {t("day_word").toUpperCase()}</span>
          </div>
          <h2 className="font-heading text-2xl font-semibold mt-3">{t("spotlight_title")}</h2>
          <p className="text-sm text-muted-foreground mt-1">{t("spotlight_desc")}</p>
          <ul className="text-sm mt-3 space-y-1">
            <li>★ {t("bullet_region_top")}</li>
            <li>★ {t("bullet_spotlight_badge")}</li>
            <li>★ {t("bullet_constant_visibility")}</li>
          </ul>
          <p className="font-heading text-xl mt-4">25,000 {t("sum_word")}</p>
          <div className="flex flex-col sm:flex-row gap-2 mt-3">
            <button
              data-testid="buy-spotlight-balance"
              onClick={() => activate("spotlight")}
              disabled={busy}
              className="flex-1 rounded-2xl bg-gold text-ink py-3 font-medium disabled:opacity-50"
            >
              {t("activate_with_balance")}
            </button>
            <button
              data-testid="buy-spotlight-click"
              onClick={() => payViaClick("spotlight", 25000)}
              className="flex-1 rounded-2xl border border-border bg-card py-3 font-medium hover:bg-muted"
            >
              CLICK
            </button>
          </div>
        </div>
      </div>

      <p className="text-xs text-muted-foreground text-center pt-2">
        💡 Spotlight + Premium = 10x konversiya
      </p>

      {/* Analytics */}
      {analytics && (
        <div className="rounded-3xl border border-border bg-card p-5" data-testid="boost-analytics">
          <h2 className="font-heading text-xl font-semibold flex items-center gap-2">
            <Activity className="w-5 h-5 text-foreground" /> Analytics
          </h2>

          {/* Boost session */}
          <div className="mt-3 rounded-2xl bg-primary/5 border border-primary/20 p-4">
            <p className="text-xs font-medium text-foreground mb-2">{t("profile_boost_title")} {analytics.boost.active ? `(${t("travel_active")})` : ""}</p>
            <div className="grid grid-cols-3 sm:grid-cols-5 gap-3">
              <StatBox icon={<Eye className="w-4 h-4" />} label={t("views_word")} value={analytics.boost.impressions} />
              <StatBox icon={<Activity className="w-4 h-4" />} label={t("views_word")} value={analytics.boost.views} />
              <StatBox icon={<Heart className="w-4 h-4" />} label="Likes" value={analytics.boost.likes} />
              <StatBox icon={<MessageSquare className="w-4 h-4" />} label="Roses" value={analytics.boost.roses} />
              <StatBox icon={<MessageSquare className="w-4 h-4" />} label="Msg" value={analytics.boost.messages} />
            </div>
          </div>

          {/* Spotlight session */}
          {analytics.spotlight.active && (
            <div className="mt-3 rounded-2xl bg-gold-light/30 border border-gold/40 p-4">
              <p className="text-xs font-medium text-gold-dark mb-2">{t("current_session")}</p>
              <div className="grid grid-cols-2 gap-3">
                <StatBox icon={<Eye className="w-4 h-4" />} label={t("views_word")} value={analytics.spotlight.impressions} />
                <StatBox icon={<Activity className="w-4 h-4" />} label={t("views_word")} value={analytics.spotlight.views} />
              </div>
            </div>
          )}

          {/* Lifetime */}
          <div className="mt-3">
            <p className="text-xs font-medium text-muted-foreground mb-2">Total</p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <StatBox icon={<Eye className="w-4 h-4" />} label={t("views_word")} value={analytics.lifetime.total_impressions} />
              <StatBox icon={<Activity className="w-4 h-4" />} label={t("views_word")} value={analytics.lifetime.total_views} />
              <StatBox icon={<Heart className="w-4 h-4" />} label="Likes" value={analytics.lifetime.total_likes} />
              <StatBox icon={<Sparkles className="w-4 h-4" />} label="Gifts" value={(analytics.lifetime.gifts_received || 0).toLocaleString() + " " + t("sum_word")} />
            </div>
          </div>
        </div>
      )}

      {/* Leaderboard */}
      {leaderboard.length > 0 && (
        <div className="rounded-3xl border border-border bg-card p-5" data-testid="boost-leaderboard">
          <h2 className="font-heading text-xl font-semibold flex items-center gap-2">
            <Trophy className="w-5 h-5 text-gold-dark" /> {t("leaderboard_title")}
          </h2>
          <p className="text-xs text-muted-foreground mt-1">{t("leaderboard_desc")}</p>
          <div className="mt-3 space-y-2">
            {leaderboard.map((u, i) => (
              <div key={u.user_id || u.id || i} className="flex items-center gap-3 py-2 border-b border-border/30 last:border-0">
                <span className={`text-xs font-semibold w-6 text-center ${i === 0 ? "text-gold-dark" : i === 1 ? "text-gray-500" : i === 2 ? "text-amber-700" : "text-muted-foreground"}`}>
                  #{i + 1}
                </span>
                <div className="w-9 h-9 rounded-full bg-muted overflow-hidden">
                  {u.photo_url && <img loading="lazy" decoding="async" src={photoSrc(u.photo_url)} alt="" className="w-full h-full object-cover" />}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{u.name}, {u.age}</p>
                  <p className="text-[11px] text-muted-foreground">{u.city || u.region}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold text-foreground">{(u.ranking_score || u.boost_impressions || 0).toLocaleString()}</p>
                  <p className="text-[10px] text-muted-foreground">{t("views_word")}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatBox({ icon, label, value }) {
  return (
    <div className="rounded-xl bg-card border border-border/40 p-2 text-center">
      <div className="text-muted-foreground flex items-center justify-center gap-1 text-[10px]">{icon}{label}</div>
      <p className="text-lg font-heading font-semibold mt-0.5">{value}</p>
    </div>
  );
}
