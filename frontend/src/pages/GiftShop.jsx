import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Search, User, Plus, ArrowRight, X, PackageOpen } from "lucide-react";
import { useApp } from "@/contexts/AppContext";
import { photoSrc } from "@/lib/photo";
import { PageHead, SectionLabel, Segmented, EmptyState, CTA } from "@/components/kit";
import {
  useGiftCatalog, usePlanGiftCatalog, useGiftInventory, useGiftRecipients, usePurchaseGift, useRedeemGift,
} from "@/hooks/queries";
import { giftGradient, GIFT_PLAN_ICONS } from "@/lib/giftVisuals";

// Full-bleed gradient tiles, not a small icon in a white box - a static
// emoji reads as "premium" only when it's the hero of a rich card, not a
// tiny picture bolted onto plain white. Gradients themselves live in
// giftVisuals.js, shared with the chat bubble a delivered gift renders as.
const TIER_META = {
  care:   { label_uz: "E'tibor", label_ru: "Забота", label_en: "Care" },
  love:   { label_uz: "Sevgi",   label_ru: "Любовь", label_en: "Love" },
  luxury: { label_uz: "Hashamat",label_ru: "Люкс",   label_en: "Luxury" },
};
const TIER_ORDER = ["care", "love", "luxury"];

function labelFor(lang, item) {
  return lang === "ru" ? item.label_ru : lang === "en" ? item.label_en : item.label_uz;
}

function tierLabel(lang, tk) {
  const tm = TIER_META[tk];
  return lang === "ru" ? tm.label_ru : lang === "en" ? tm.label_en : tm.label_uz;
}

// The one card component every gift (decorative or subscription) renders
// through - a full gradient tile with a glowing hero emoji, a frosted chip
// and bold price, instead of a small icon-in-a-circle sitting on white.
// Every tile always looks fully "alive" regardless of balance - an
// insufficient-balance tap routes straight to top-up instead of the tile
// sitting there dimmed and doing nothing when pressed.
function GiftTile({ emoji, title, price, gradient, chip, onClick, testid }) {
  return (
    <button
      onClick={onClick}
      data-testid={testid}
      className={`group relative overflow-hidden rounded-3xl h-[150px] p-3 flex flex-col text-white shadow-lg bg-gradient-to-br ${gradient} transition hover:-translate-y-1 hover:shadow-2xl active:scale-95`}
    >
      <span className="absolute inset-0 bg-gradient-to-br from-white/25 via-transparent to-black/10 pointer-events-none" />
      {chip && (
        <span className="relative self-start text-[9px] font-bold uppercase tracking-wider bg-black/25 backdrop-blur-sm px-2 py-0.5 rounded-full">
          {chip}
        </span>
      )}
      <span className="relative flex-1 grid place-items-center">
        <span className="absolute w-14 h-14 rounded-full bg-white/25 blur-xl" />
        <span className="relative text-4xl drop-shadow-[0_4px_10px_rgba(0,0,0,0.35)]">{emoji}</span>
      </span>
      <span className="relative text-center">
        <p className="text-xs font-semibold leading-tight line-clamp-2">{title}</p>
        <p className="text-sm font-bold tabular-nums mt-0.5">
          {price.toLocaleString()} <span className="text-[10px] font-medium opacity-80">so'm</span>
        </p>
      </span>
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
// same search-and-pick UX either way. `disabled` (true while the purchase/
// redeem mutation is in flight) blocks every row AND shows a blocking
// overlay - without this, a slow network reply reads as "did nothing
// happen?" and repeated taps fire the purchase multiple times.
function RecipientPicker({ onPick, onClose, disabled }) {
  const { t } = useApp();
  const [q, setQ] = useState("");
  const { data: recipients = [], isLoading } = useGiftRecipients(q);

  return (
    <div className="fixed inset-0 flex items-end sm:items-center sm:justify-center" style={{ zIndex: 10003 }} data-testid="gift-recipient-picker">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={disabled ? undefined : onClose} />
      <div className="relative w-full sm:max-w-md bg-card rounded-t-3xl sm:rounded-3xl shadow-2xl max-h-[85vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-border/40 shrink-0">
          <h3 className="font-heading text-lg font-semibold">{t("gift_pick_recipient_title")}</h3>
          <button onClick={onClose} disabled={disabled} className="p-2 rounded-full hover:bg-muted disabled:opacity-30"><X className="w-4 h-4" /></button>
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
        <div className="relative flex-1 min-h-0 overflow-y-auto p-2">
          {disabled && (
            <div className="absolute inset-0 z-10 flex items-center justify-center bg-card/80 backdrop-blur-sm" data-testid="gift-sending-overlay">
              <p className="text-sm font-medium text-muted-foreground">{t("gift_sending")}</p>
            </div>
          )}
          {isLoading && <p className="text-center text-sm text-muted-foreground py-6">{t("loading")}</p>}
          {!isLoading && recipients.length === 0 && (
            <EmptyState icon={<User className="w-6 h-6" />} title={t("gift_no_recipients")} />
          )}
          {recipients.map((r) => (
            <button
              key={r.id}
              onClick={() => onPick(r)}
              disabled={disabled}
              data-testid={`gift-recipient-${r.id}`}
              className="w-full flex items-center gap-3 p-2.5 rounded-2xl hover:bg-muted transition text-left disabled:opacity-50"
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

function itemEmoji(item) {
  if (item.category === "plan") return GIFT_PLAN_ICONS[item.plan] || "🎁";
  return item.emoji;
}

// The purchase flow for a freshly-picked catalog item: ask who it's for,
// then either confirm-into-inventory or hand off to the recipient picker.
// A subscription gift (category "plan") always goes straight to the
// recipient picker - gifting a plan to yourself is just buying it.
//
// submittedRef is a hard lock, separate from purchase.isPending - React's
// state update from the first tap can lag a frame behind a fast second tap,
// and on a slow connection that gap is exactly what turned "the app looks
// frozen" into 10-15 duplicate sends draining a real balance. The ref flips
// synchronously on the very first call, before any re-render.
function PurchaseFlow({ item, lang, onClose, onDone }) {
  const { t, refresh } = useApp();
  const isPlan = item.category === "plan";
  const [step, setStep] = useState(isPlan ? "pick" : "who");
  const purchase = usePurchaseGift();
  const submittedRef = React.useRef(false);

  const buyForSelf = () => {
    if (submittedRef.current) return;
    submittedRef.current = true;
    purchase.mutate({ giftKind: item.kind }, {
      onSuccess: () => {
        toast.success(t("gift_bought_for_self").replace("{emoji}", item.emoji).replace("{label}", labelFor(lang, item)));
        refresh();
        onDone();
      },
      onError: (e) => {
        submittedRef.current = false;
        toast.error(e?.response?.status === 402 ? t("gift_need_topup") : t("error_generic"));
      },
    });
  };

  const buyForRecipient = (recipient) => {
    if (submittedRef.current) return;
    submittedRef.current = true;
    purchase.mutate({ giftKind: item.kind, toUserId: recipient.id }, {
      onSuccess: () => {
        toast.success(t("gift_sent_to_named").replace("{emoji}", item.emoji).replace("{name}", recipient.name));
        refresh();
        onDone();
      },
      onError: (e) => {
        submittedRef.current = false;
        toast.error(e?.response?.status === 402 ? t("gift_need_topup") : t("error_generic"));
      },
    });
  };

  if (step === "pick") {
    return <RecipientPicker onPick={buyForRecipient} onClose={isPlan ? onClose : () => setStep("who")} disabled={purchase.isPending} />;
  }

  return (
    <div className="fixed inset-0 flex items-end sm:items-center sm:justify-center" style={{ zIndex: 10002 }} data-testid="gift-purchase-flow">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full sm:max-w-sm bg-card rounded-t-3xl sm:rounded-3xl shadow-2xl p-5">
        <button onClick={onClose} className="absolute top-4 right-4 p-2 rounded-full hover:bg-muted"><X className="w-4 h-4" /></button>
        <div className="text-center mb-5">
          <div className={`w-20 h-20 mx-auto rounded-3xl grid place-items-center bg-gradient-to-br ${giftGradient(item)} mb-3 shadow-lg`}>
            <span className="text-4xl drop-shadow-[0_4px_10px_rgba(0,0,0,0.35)]">{itemEmoji(item)}</span>
          </div>
          <p className="font-heading text-lg font-semibold">{labelFor(lang, item)}</p>
          <p className="text-sm font-bold tabular-nums mt-1">{item.price.toLocaleString()} <span className="text-xs font-medium text-muted-foreground">so'm</span></p>
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
  const { t, refresh } = useApp();
  const { data: items = [], isLoading } = useGiftInventory();
  const [redeeming, setRedeeming] = useState(null);
  const redeem = useRedeemGift();
  const submittedRef = React.useRef(false);

  const use = (recipient) => {
    if (submittedRef.current) return;
    submittedRef.current = true;
    redeem.mutate({ itemId: redeeming.id, toUserId: recipient.id }, {
      onSuccess: () => {
        toast.success(t("gift_sent_to_named").replace("{emoji}", redeeming.emoji).replace("{name}", recipient.name));
        refresh();
        submittedRef.current = false;
        setRedeeming(null);
      },
      onError: () => {
        submittedRef.current = false;
        toast.error(t("error_generic"));
        setRedeeming(null);
      },
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
          <div className={`w-12 h-12 rounded-2xl grid place-items-center bg-gradient-to-br ${giftGradient(it)} shrink-0 shadow`}>
            <span className="text-2xl drop-shadow">{it.emoji}</span>
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold truncate">{labelFor(lang, it)}</p>
            <p className="text-xs text-muted-foreground">{it.price.toLocaleString()} so'm</p>
          </div>
          <CTA onClick={() => setRedeeming(it)} className="!w-auto px-4 !py-2 text-sm shrink-0" data-testid={`gift-use-${it.id}`}>
            {t("gift_use_button")}
          </CTA>
        </div>
      ))}
      {redeeming && <RecipientPicker onPick={use} onClose={() => setRedeeming(null)} disabled={redeem.isPending} />}
    </div>
  );
}

export default function GiftShop() {
  const { user, t, lang } = useApp();
  const navigate = useNavigate();
  const [tab, setTab] = useState("shop");
  const { data: catalog, isLoading } = useGiftCatalog();
  const { data: planCatalog, isLoading: planLoading } = usePlanGiftCatalog();
  const [picked, setPicked] = useState(null);

  const groups = React.useMemo(() => {
    const g = { care: [], love: [], luxury: [] };
    (catalog?.items || []).forEach((it) => { if (g[it.tier]) g[it.tier].push(it); });
    return g;
  }, [catalog]);

  const balance = user?.balance || 0;

  // Every tile stays fully visible and tappable, affordable or not - an
  // unaffordable tap goes straight to the balance top-up instead of the
  // tile just sitting there dimmed and doing nothing when pressed.
  const onPickGift = (item) => {
    if (item.price > balance) {
      toast.info(t("gift_need_topup"));
      navigate("/premium?tab=balance");
      return;
    }
    setPicked(item);
  };

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
        <div className="space-y-6">
          {(isLoading || planLoading) && <p className="text-center text-sm text-muted-foreground py-10">{t("loading")}</p>}

          {!isLoading && TIER_ORDER.map((tk) => {
            const list = groups[tk];
            if (!list || list.length === 0) return null;
            return (
              <div key={tk}>
                <SectionLabel>{tierLabel(lang, tk)}</SectionLabel>
                <div className="grid grid-cols-3 gap-2.5 mt-2">
                  {list.map((it) => (
                    <GiftTile
                      key={it.kind}
                      emoji={itemEmoji(it)}
                      title={labelFor(lang, it)}
                      price={it.price}
                      gradient={giftGradient(it)}
                      onClick={() => onPickGift(it)}
                      testid={`giftshop-card-${it.kind}`}
                    />
                  ))}
                </div>
              </div>
            );
          })}

          {!planLoading && planCatalog?.items?.length > 0 && (
            <div>
              <SectionLabel>{t("gift_plan_section_title")}</SectionLabel>
              <p className="text-xs text-muted-foreground -mt-1 mb-2">{t("gift_plan_section_hint")}</p>
              <div className="grid grid-cols-2 gap-2.5">
                {planCatalog.items.map((it) => (
                  <GiftTile
                    key={it.kind}
                    emoji={itemEmoji(it)}
                    title={labelFor(lang, it)}
                    price={it.price}
                    gradient={giftGradient(it)}
                    onClick={() => onPickGift(it)}
                    testid={`giftshop-plan-card-${it.kind}`}
                  />
                ))}
              </div>
            </div>
          )}
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
