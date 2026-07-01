import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { Crown, Check, Wallet } from "lucide-react";
import { toast } from "sonner";

const PLANS = [
  {
    key: "free", title: "Free", price: 0,
    features: ["profile", "candidates", "saved", "likes", "matches", "chat_replies"],
    style: "bg-card border border-border",
  },
  {
    key: "standard", title: "Standard", price: 19900,
    features: ["chat_unlimited", "candidates", "saved", "more_filters"],
    style: "bg-card border-2 border-secondary",
    badge: "✅",
  },
  {
    key: "premium", title: "Premium", price: 79000,
    features: ["chat_unlimited", "who_viewed", "who_saved", "who_interested", "more_filters", "boost_visibility"],
    style: "bg-card border-2 border-gold shadow-premium",
    badge: "💎",
  },
  {
    key: "vip", title: "VIP", price: 199000,
    features: ["max_visibility", "stealth_view", "priority", "vip_badge", "travel_mode", "family_share"],
    style: "bg-ink text-white border border-white/10",
    badge: "👑",
  },
];

const FEATURE_LABELS = {
  uz: {
    profile: "Profil", candidates: "Nomzodlar", saved: "Saqlash", likes: "Yoqtirishlar", matches: "Moslashuvlar", chat_replies: "Javob yozish",
    chat_unlimited: "Cheksiz yozishish",
    who_viewed: "Kim ko'rdi", who_saved: "Kim saqladi", who_interested: "Kim qiziqdi", more_filters: "Ko'proq filtrlar", boost_visibility: "Ko'rinishni oshirish",
    max_visibility: "Maksimal ko'rinish", stealth_view: "Maxfiy ko'rish", priority: "Priority", vip_badge: "VIP badge", travel_mode: "Sayohat rejimi", family_share: "Oila ulashish",
  },
  ru: {
    profile: "Профиль", candidates: "Кандидаты", saved: "Сохранять", likes: "Лайки", matches: "Совпадения", chat_replies: "Ответы в чате",
    chat_unlimited: "Безлимитные сообщения",
    who_viewed: "Кто видел", who_saved: "Кто сохранил", who_interested: "Кто интересуется", more_filters: "Больше фильтров", boost_visibility: "Увеличение видимости",
    max_visibility: "Максимум видимости", stealth_view: "Скрытый просмотр", priority: "Приоритет", vip_badge: "VIP badge", travel_mode: "Режим путешествия", family_share: "Семейный доступ",
  },
  en: {
    profile: "Profile", candidates: "Candidates", saved: "Save", likes: "Likes", matches: "Matches", chat_replies: "Chat replies",
    chat_unlimited: "Unlimited messaging",
    who_viewed: "Who viewed", who_saved: "Who saved", who_interested: "Who interested", more_filters: "More filters", boost_visibility: "Boost visibility",
    max_visibility: "Max visibility", stealth_view: "Stealth view", priority: "Priority", vip_badge: "VIP badge", travel_mode: "Travel mode", family_share: "Family share",
  },
};

export default function Premium() {
  const { t, lang, user, refresh } = useApp();
  const [sp] = useSearchParams();
  const tab = sp.get("tab") || "plans";
  const showTopup = sp.get("topup") === "1";
  const [topupAmount, setTopupAmount] = useState(50000);
  const [creating, setCreating] = useState(false);
  const [payments, setPayments] = useState([]);

  useEffect(() => {
    api.get("/payments/mine").then((r) => setPayments(r.data || []));
  }, []);

  useEffect(() => {
    if (tab) {
      const element = document.getElementById(`premium-${tab}`);
      if (element) {
        element.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }
  }, [tab]);

  const buy = async (purpose) => {
    setCreating(true);
    try {
      const r = await api.post("/payments/create", { purpose });
      toast.success(t("pay_with_click"));
      window.open(r.data.payment_link, "_blank");
      setPayments((p) => [{ ...r.data, purpose, user_id: user.id, created_at: new Date() }, ...p]);
    } catch (e) {
      toast.error(t("error_generic"));
    } finally { setCreating(false); }
  };
  const topup = async () => {
    setCreating(true);
    try {
      const r = await api.post("/payments/create", { purpose: "balance_topup", amount: topupAmount });
      window.open(r.data.payment_link, "_blank");
      setPayments((p) => [{ ...r.data, purpose: "balance_topup" }, ...p]);
    } catch (e) {
      toast.error(t("error_generic"));
    } finally { setCreating(false); }
  };

  const labels = FEATURE_LABELS[lang] || FEATURE_LABELS.uz;

  return (
    <div className="px-4 md:px-8 pt-6 pb-8 space-y-6">
      <div>
        <h1 className="font-heading text-3xl font-semibold tracking-tight">{t("premium")}</h1>
        <p className="text-sm text-muted-foreground mt-1">{t("tagline")}</p>
      </div>

      {/* Subscription Plans - Recurring Monthly Access */}
      <div id="premium-plans">
        <div className="flex items-center gap-2 mb-2">
          <Crown className="w-5 h-5 text-gold" />
          <p className="text-sm uppercase tracking-wider text-muted-foreground font-medium">{t("premium_section_plans")}</p>
        </div>
        <p className="text-xs text-muted-foreground mb-3">{t("premium_section_plans_desc")}</p>
        <div className="space-y-3 stagger">
          {PLANS.map((p) => {
            const isCurrent = user?.plan === p.key;
            return (
              <div
                key={p.key}
                data-testid={`plan-${p.key}`}
                className={`rounded-3xl p-5 ${p.style} ${isCurrent ? "ring-2 ring-primary" : ""}`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-heading text-2xl font-semibold flex items-center gap-2">
                      {p.title} {p.badge}
                    </p>
                    <p className="text-xs opacity-70 mt-0.5">
                      {p.price === 0 ? t("plan_free_desc") : t(`plan_${p.key}_desc`)}
                    </p>
                  </div>
                  <p className="font-heading text-xl">
                    {p.price === 0 ? t("plan_free_title") : `${p.price.toLocaleString()} ${t("sum")}`}
                  </p>
                </div>
                <ul className="mt-3 space-y-1.5">
                  {p.features.map((f) => (
                    <li key={f} className="text-sm flex items-center gap-2">
                      <Check className="w-3.5 h-3.5 opacity-70" /> {labels[f]}
                    </li>
                  ))}
                </ul>
                {p.key !== "free" && !isCurrent && (
                  <button
                    data-testid={`buy-${p.key}`}
                    onClick={() => buy(p.key)}
                    disabled={creating}
                    className={`mt-4 w-full rounded-2xl py-3 font-medium ${
                      p.key === "vip" ? "bg-ink text-gold border border-gold/30" : "bg-primary text-white"
                    }`}
                  >
                    {t("buy")} · {t("pay_with_click")}
                  </button>
                )}
                {isCurrent && <p className="mt-3 text-sm font-medium text-secondary">— {t("current_plan")} —</p>}
              </div>
            );
          })}
        </div>
      </div>

      {/* Internal Balance - For Gifts, Boost, AI Features */}
      <div id="premium-balance" className="rounded-3xl bg-card border border-border p-5" data-testid="topup-section">
        <div className="flex items-center gap-2 mb-3">
          <Wallet className="w-5 h-5 text-primary" />
          <p className="font-heading text-xl font-semibold">{t("topup_balance")}</p>
        </div>
        <p className="text-xs text-muted-foreground mb-3">{t("premium_section_balance_hint")}</p>
        <p className="text-xs text-secondary mb-3">{t("premium_section_balance_usage")}</p>
        <div className="flex gap-2 mb-3">
          {[10000, 50000, 100000, 200000].map((v) => (
            <button
              key={v}
              data-testid={`topup-${v}`}
              onClick={() => setTopupAmount(v)}
              className={`flex-1 rounded-xl border py-2 text-sm ${
                topupAmount === v ? "bg-primary text-white border-primary" : "bg-card border-border"
              }`}
            >
              {(v / 1000).toFixed(0)}k
            </button>
          ))}
        </div>
        <button
          data-testid="topup-pay"
          onClick={topup}
          disabled={creating}
          className="w-full rounded-2xl bg-secondary text-white py-3 font-medium"
        >
          {t("pay_with_click")} · {topupAmount.toLocaleString()} {t("sum")}
        </button>
      </div>

      {/* Roses - Quick Attention Currency */}
      <div id="premium-roses" className="rounded-3xl bg-primary/5 border-2 border-primary/30 p-5" data-testid="roses-section">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xl">🌹</span>
          <p className="font-heading text-xl font-semibold">{t("premium_section_roses")}</p>
        </div>
        <p className="text-sm mt-1 text-muted-foreground">{t("premium_section_roses_desc")}</p>
        <p className="text-xs text-secondary mt-1">{t("premium_section_roses_usage")}</p>
        <div className="grid grid-cols-3 gap-2 mt-3">
          {[["1", 1, 5000], ["5", 5, 20000], ["12", 12, 45000]].map(([k, count, price]) => (
            <button
              key={k}
              data-testid={`roses-${k}`}
              onClick={async () => {
                setCreating(true);
                try {
                  const r = await api.post("/roses/purchase", { bundle: k });
                  window.open(r.data.payment_link, "_blank");
                  toast.success(t("roses_payment_opened").replace("{count}", count));
                } catch (e) { toast.error("Xato"); } finally { setCreating(false); }
              }}
              disabled={creating}
              className="rounded-2xl bg-card border border-border hover:border-primary p-3 text-center transition"
            >
              <p className="text-2xl">🌹</p>
              <p className="font-medium text-sm mt-1">{count} ta</p>
              <p className="text-xs text-muted-foreground">{price.toLocaleString()} {t("sum")}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Super-Application - One-Time Filter Bypass */}
      <div className="rounded-3xl bg-gold-light/40 border border-gold/40 p-5" data-testid="super-section">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xl">✨</span>
          <p className="font-heading text-xl font-semibold">{t("super_application")}</p>
        </div>
        <p className="text-sm mt-1 text-muted-foreground">{t("premium_section_super_desc")}</p>
        <p className="text-xs text-secondary mt-1">{t("premium_section_super_usage")}</p>
        <button
          data-testid="buy-super"
          onClick={() => buy("super_application")}
          disabled={creating}
          className="mt-3 w-full rounded-2xl bg-gradient-to-r from-gold to-gold-dark text-white py-3 font-medium"
        >
          {t("buy_super")} · 15,000 {t("sum")}
        </button>
      </div>

      {/* Concierge — premium manual matching */}
      <div className="rounded-3xl bg-gradient-to-br from-secondary/10 via-primary/5 to-gold-light/30 border-2 border-secondary/40 p-5" data-testid="concierge-section">
        <p className="font-heading text-xl font-semibold flex items-center gap-2">👑 {t("concierge_title")}</p>
        <p className="text-sm mt-1 text-muted-foreground">{t("concierge_desc")}</p>
        <ul className="text-xs mt-3 space-y-1 text-foreground/80">
          <li>✓ {t("premium_section_concierge_features_1")}</li>
          <li>✓ {t("premium_section_concierge_features_2")}</li>
          <li>✓ {t("premium_section_concierge_features_3")}</li>
        </ul>
        <Link
          to="/concierge"
          data-testid="concierge-link"
          className="mt-3 block w-full text-center rounded-2xl bg-secondary text-white py-3 font-medium"
        >
          {t("premium_section_concierge_btn").replace("{price}", "199,000").replace("{currency}", t("sum"))}
        </Link>
      </div>

      {/* Payments history */}
      <div>
        <p className="font-heading text-lg font-semibold mb-2">{t("payments")}</p>
        <div className="space-y-2">
          {payments.length === 0 && <p className="text-sm text-muted-foreground">{t("no_data")}</p>}
          {payments.map((p) => (
            <div key={p.id} className="rounded-2xl bg-card border border-border p-3 flex items-center justify-between" data-testid={`payment-${p.id}`}>
              <div>
                <p className="text-sm font-medium">{p.purpose}</p>
                <p className="text-xs text-muted-foreground">{p.amount?.toLocaleString()} {t("sum")}</p>
              </div>
              <span className={`text-xs px-2 py-1 rounded-full ${
                p.status === "success" ? "bg-secondary/10 text-secondary" : p.status === "failed" ? "bg-red-50 text-red-700" : "bg-gold-light text-yellow-900"
              }`}>
                {t(`payment_${p.status}`)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
