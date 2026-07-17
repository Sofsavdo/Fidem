import React, { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Sparkles, Search, User, Plus, ArrowRight, X, PackageOpen } from "lucide-react";
import { useApp } from "@/contexts/AppContext";
import { photoSrc } from "@/lib/photo";
import { PageHead, SectionLabel, Segmented, Price, EmptyState, CTA } from "@/components/kit";
import {
  useGiftCatalog, useGiftInventory, useGiftRecipients, usePurchaseGift, useRedeemGift,
} from "@/hooks/queries";

const TIER_META = {
  free:   { label_uz: "Bepul", label_ru: "Бесплатно", label_en: "Free", ring: "from-emerald-400/30 to-emerald-400/5", chip: "bg-emerald-100 text-emerald-800" },
  care:   { label_uz: "E'tibor", label_ru: "Забота", label_en: "Care", ring: "from-secondary/35 to-secondary/5", chip: "bg-secondary/10 text-secondary" },
  love:   { label_uz: "Sevgi", label_ru: "Любовь", label_en: "Love", ring: "from-primary/35 to-primary/5", chip: "bg-primary/10 text-primary" },
  luxury: { label_uz: "Hashamat", label_ru: "Люкс", label_en: "Luxury", ring: "from-gold to-gold-light/40", chip: "bg-gold-light/60 text-gold-dark" },
};
const TIER_ORDER = ["free", "care", "love", "luxury"];

function labelFor(lang, item) {
  return lang === "ru" ? item.label_ru : lang === "en" ? item.label_en : item.label_uz;
}

// Premium card: a large tier-gradient badge behind the emoji instead of a
// bare icon in a row, name + price given real typographic weight - the
// "raketa emas" complaint was about presentation, not the emoji itself.
function GiftCard({ item, lang, disabled, onPick }) {
  const tier = TIER_META[item.tier] || TIER_META.care;
  return (
    <button
      onClick={() => onPick(item)}
      disabled={disabled}
      data-testid={`giftshop-card-${item.kind}`}
      className={`group rounded-3xl border border-border bg-card p-4 flex flex-col items-center gap-2 transition ${
        disabled ? "opacity-40" : "hover:-translate-y-1 hover:shadow-lg active:scale-95"
      }`}
    >
      <div className={`w-16 h-16 rounded-full grid place-items-center bg-gradient-to-br ${tier.ring} shadow-inner`}>
        <span className="text-3xl leading-none drop-shadow-sm">{item.emoji}</span>
      </div>
      <p className="text-sm font-semibold text-center leading-tight">{labelFor(lang, item)}</p>
      {item.price > 0 ? (
        <Price amount={item.price} size="sm" />
      ) : (
        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${tier.chip}`}>{tier.label_uz}</span>
      )}
    </button>
  );
}

function Avatar({ url, size = "w-12 h-12" }) {
  return (
    <div className={`${size} rounded-full bg-muted grid place-items-center overflow-hidden shrink-0`}>
      {url ? <img src={photoSrc(url)} alt="" loading="lazy" decoding="async" className="w-full h-full object-cover" /> : <User className="w-1/2 h-1/2 text-muted-foreground" />}
    </div>
  );
}

// Shared by both "buy for someone" and "use a gift from my inventory" -
// same search-and-pick UX either way.
function RecipientPicker({ onPick, onClose }) {
  const { t } = useApp();
  const [q, setQ] = useState("");
  const { data: recipients = [], isLoading } = useGiftRecipients(q);

  return (
    <div className="fixed inset-0 flex items-end sm:items-center sm:justify-center" style={{ zIndex: 10003 }} data-testid="gift-recipient-picker">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full sm:max-w-md bg-card rounded-t-3xl sm:rounded-3xl shadow-2xl max-h-[85vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-border/40 shrink-0">
          <h3 className="font-heading text-lg font-semibold">{t("gift_pick_recipient_title")}</h3>
          <button onClick={onClose} className="p-2 rounded-full hover:bg-muted"><X className="w-4 h-4" /></button>
        </div>
        <div className="p-3 border-b border-border/40 shrink-0">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder={t("gift_search_recipient_placeholder")}
              className="w-full rounded-2xl border border-border bg-background pl-9 pr-3 py-2.5 text-sm outline-none focus:border-primary"
              data-testid="gift-recipient-search"
            />
          </div>
        </div>
        <div className="flex-1 min-h-0 overflow-y-auto p-2">
          {isLoading && <p className="text-center text-sm text-muted-foreground py-6">{t("loading")}</p>}
          {!isLoading && recipients.length === 0 && (
            <EmptyState icon={<User className="w-6 h-6" />} title={t("gift_no_recipients")} />
          )}
          {recipients.map((r) => (
            <button
              key={r.id}
              onClick={() => onPick(r)}
              data-testid={`gift-recipient-${r.id}`}
              className="w-full flex items-center gap-3 p-2.5 rounded-2xl hover:bg-muted transition text-left"
            >
              <Avatar url={r.photo_url} />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium truncate flex items-center gap-1.5">
                  {r.online && <span className="w-1.5 h-1.5 rounded-full bg-secondary shrink-0" />}
                  {r.name}, {r.age}
                </p>
                <p className="text-xs text-muted-foreground truncate">{[r.region, r.district].filter(Boolean).join(" · ")}</p>
              </div>
              <ArrowRight className="w-4 h-4 text-muted-foreground shrink-0" />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// The purchase flow for a freshly-picked catalog item: ask who it's for,
// then either confirm-into-inventory or hand off to the recipient picker.
function PurchaseFlow({ item, lang, onClose, onDone }) {
  const { t } = useApp();
  const [step, setStep] = useState("who"); // "who" | "pick"
  const purchase = usePurchaseGift();

  const buyForSelf = () => {
    purchase.mutate({ giftKind: item.kind }, {
      onSuccess: () => {
        toast.success(t("gift_bought_for_self").replace("{emoji}", item.emoji).replace("{label}", labelFor(lang, item)));
        onDone();
      },
      onError: (e) => toast.error(e?.response?.status === 402 ? t("gift_need_topup") : t("error_generic")),
    });
  };

  const buyForRecipient = (recipient) => {
    purchase.mutate({ giftKind: item.kind, toUserId: recipient.id }, {
      onSuccess: () => {
        toast.success(t("gift_sent_to_named").replace("{emoji}", item.emoji).replace("{name}", recipient.name));
        onDone();
      },
      onError: (e) => toast.error(e?.response?.status === 402 ? t("gift_need_topup") : t("error_generic")),
    });
  };

  if (step === "pick") {
    return <RecipientPicker onPick={buyForRecipient} onClose={() => setStep("who")} />;
  }

  return (
    <div className="fixed inset-0 flex items-end sm:items-center sm:justify-center" style={{ zIndex: 10002 }} data-testid="gift-purchase-flow">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full sm:max-w-sm bg-card rounded-t-3xl sm:rounded-3xl shadow-2xl p-5">
        <button onClick={onClose} className="absolute top-4 right-4 p-2 rounded-full hover:bg-muted"><X className="w-4 h-4" /></button>
        <div className="text-center mb-5">
          <div className={`w-20 h-20 mx-auto rounded-full grid place-items-center bg-gradient-to-br ${(TIER_META[item.tier] || TIER_META.care).ring} mb-3`}>
            <span className="text-4xl">{item.emoji}</span>
          </div>
          <p className="font-heading text-lg font-semibold">{labelFor(lang, item)}</p>
          {item.price > 0 && <Price amount={item.price} className="mt-1" />}
        </div>
        <p className="text-sm font-medium text-center mb-3">{t("gift_who_for_question")}</p>
        <div className="space-y-2">
          <button
            onClick={buyForSelf}
            disabled={purchase.isPending}
            data-testid="gift-choose-self"
            className="w-full text-left rounded-2xl border border-border p-3.5 hover:border-primary/50 hover:bg-primary/5 transition disabled:opacity-50"
          >
            <p className="text-sm font-semibold flex items-center gap-2"><PackageOpen className="w-4 h-4 text-primary" /> {t("gift_option_self_title")}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{t("gift_option_self_hint")}</p>
          </button>
          <button
            onClick={() => setStep("pick")}
            disabled={purchase.isPending}
            data-testid="gift-choose-other"
            className="w-full text-left rounded-2xl border border-border p-3.5 hover:border-primary/50 hover:bg-primary/5 transition disabled:opacity-50"
          >
            <p className="text-sm font-semibold flex items-center gap-2"><ArrowRight className="w-4 h-4 text-primary" /> {t("gift_option_other_title")}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{t("gift_option_other_hint")}</p>
          </button>
        </div>
        {purchase.isPending && <p className="text-center text-xs text-muted-foreground mt-3">{t("gift_sending")}</p>}
      </div>
    </div>
  );
}

function InventoryTab({ lang }) {
  const { t } = useApp();
  const { data: items = [], isLoading } = useGiftInventory();
  const [redeeming, setRedeeming] = useState(null);
  const redeem = useRedeemGift();

  const use = (recipient) => {
    redeem.mutate({ itemId: redeeming.id, toUserId: recipient.id }, {
      onSuccess: () => {
        toast.success(t("gift_sent_to_named").replace("{emoji}", redeeming.emoji).replace("{name}", recipient.name));
        setRedeeming(null);
      },
      onError: () => { toast.error(t("error_generic")); setRedeeming(null); },
    });
  };

  if (isLoading) return <p className="text-center text-sm text-muted-foreground py-10">{t("loading")}</p>;
  if (items.length === 0) {
    return (
      <EmptyState
        icon={<PackageOpen className="w-6 h-6" />}
        title={t("gift_inventory_empty_title")}
        hint={t("gift_inventory_empty_hint")}
      />
    );
  }

  return (
    <div className="space-y-2">
      {items.map((it) => (
        <div key={it.id} className="rounded-2xl border border-border bg-card p-3 flex items-center gap-3" data-testid={`gift-inv-${it.id}`}>
          <div className={`w-12 h-12 rounded-full grid place-items-center bg-gradient-to-br ${(TIER_META[it.price === 0 ? "free" : "care"]).ring} shrink-0`}>
            <span className="text-2xl">{it.emoji}</span>
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold truncate">{labelFor(lang, it)}</p>
            <p className="text-xs text-muted-foreground">{it.price > 0 ? `${it.price.toLocaleString()} so'm` : t("gift_free_word")}</p>
          </div>
          <CTA onClick={() => setRedeeming(it)} className="!w-auto px-4 !py-2 text-sm shrink-0" data-testid={`gift-use-${it.id}`}>
            {t("gift_use_button")}
          </CTA>
        </div>
      ))}
      {redeeming && <RecipientPicker onPick={use} onClose={() => setRedeeming(null)} />}
    </div>
  );
}

export default function GiftShop() {
  const { user, t, lang } = useApp();
  const [tab, setTab] = useState("shop");
  const { data: catalog, isLoading } = useGiftCatalog();
  const [picked, setPicked] = useState(null);

  const groups = React.useMemo(() => {
    const g = { free: [], care: [], love: [], luxury: [] };
    (catalog?.items || []).forEach((it) => { if (g[it.tier]) g[it.tier].push(it); });
    return g;
  }, [catalog]);

  const balance = user?.balance || 0;

  return (
    <div className="p-4 space-y-5" data-testid="gift-shop-page">
      <PageHead title={t("gift_shop_title")} subtitle={t("gift_shop_subtitle")} />

      <div className="rounded-3xl bg-gradient-to-br from-secondary/15 via-card to-gold-light/20 border border-secondary/25 p-4 flex items-center justify-between">
        <div>
          <SectionLabel>{t("app_balance_title")}</SectionLabel>
          <p className="font-heading text-2xl font-bold tabular-nums mt-0.5">{balance.toLocaleString()} <span className="text-sm font-medium opacity-60">{t("sum")}</span></p>
        </div>
        <Link to="/premium?tab=balance" data-testid="giftshop-topup-link" className="inline-flex items-center gap-1 rounded-full bg-secondary text-white px-3.5 py-2 text-xs font-semibold shrink-0">
          <Plus className="w-3.5 h-3.5" /> {t("topup_balance")}
        </Link>
      </div>

      <Segmented
        options={[
          { key: "shop", label: t("gift_tab_shop") },
          { key: "inventory", label: t("gift_tab_inventory") },
        ]}
        value={tab}
        onChange={setTab}
      />

      {tab === "shop" && (
        <div className="space-y-5">
          {isLoading && <p className="text-center text-sm text-muted-foreground py-10">{t("loading")}</p>}
          {!isLoading && TIER_ORDER.map((tk) => {
            const list = groups[tk];
            if (!list || list.length === 0) return null;
            const tm = TIER_META[tk];
            return (
              <div key={tk}>
                <div className="flex items-center gap-2 mb-2">
                  <SectionLabel>{tm[lang === "ru" ? "label_ru" : lang === "en" ? "label_en" : "label_uz"]}</SectionLabel>
                  {tk === "free" && catalog && (
                    <span className="text-[10px] text-secondary inline-flex items-center gap-1"><Sparkles className="w-3 h-3" /> {catalog.free_remaining}/{catalog.free_quota_per_week} {t("gift_free_word")}</span>
                  )}
                </div>
                <div className="grid grid-cols-3 gap-2.5">
                  {list.map((it) => (
                    <GiftCard key={it.kind} item={it} lang={lang} disabled={it.price > balance && it.tier !== "free"} onPick={setPicked} />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {tab === "inventory" && <InventoryTab lang={lang} />}

      {picked && (
        <PurchaseFlow
          item={picked}
          lang={lang}
          onClose={() => setPicked(null)}
          onDone={() => setPicked(null)}
        />
      )}
    </div>
  );
}
