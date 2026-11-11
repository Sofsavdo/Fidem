import React, { useEffect, useState, useCallback, useMemo } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useApp } from "@/contexts/AppContext";
import { purchasePlan } from "@/lib/purchase";
import { Lock, Bookmark, Crown, Camera, Check, X } from "lucide-react";
import { toast } from "sonner";
import { photoSrc } from "@/lib/photo";
import { useSaved, usePhotoRequests, useDecidePhotoRequest } from "@/hooks/queries";
import { EmptyState } from "@/components/kit";
import PhotoFill from "@/components/PhotoFill";

// Three lists are enough: who I liked, who is interested in me (it already
// includes everyone who saved me), and who looked at my profile. Photo
// requests are only needed by people who closed their photos, so that tab
// shows up only while a request is waiting.
const TABS = [
  { k: "mine", labelKey: "saved_by_me" },
  { k: "interested", labelKey: "interested_in_me" },
  { k: "viewers", labelKey: "viewed_my_profile" },
  { k: "requests", labelKey: "photo_requests_tab" },
];
const TAB_ALIAS = { by_others: "interested" };

// Cheapest plan that unlocks these lists — mirrors PLANS.premium in Premium.jsx.
const UNLOCK_PRICE = 79000;

export default function Saved() {
  const { t, user, refresh } = useApp();
  const navigate = useNavigate();
  const [buying, setBuying] = useState(false);
  const buyPremium = async () => {
    if (buying) return;
    setBuying(true);
    try { await purchasePlan("premium", { t, navigate, onPaid: refresh }); } finally { setBuying(false); }
  };
  const [searchParams, setSearchParams] = useSearchParams();
  const [tab, setTab] = useState("mine");

  useEffect(() => {
    const raw = searchParams.get("tab");
    const q = TAB_ALIAS[raw] || raw;
    if (q && TABS.some((x) => x.k === q)) setTab(q);
  }, [searchParams]);

  // "requests" is not a saved list (its data comes from usePhotoRequests below).
  const { data: items = [], isLoading } = useSaved(tab, { enabled: tab !== "requests" });
  // Incoming photo-permission requests: always fetched so the tab chip can
  // show a count badge even before the tab is opened.
  const { data: photoRequests = [] } = usePhotoRequests();
  const decideMutation = useDecidePhotoRequest();
  const isPremium = ["premium", "vip"].includes(user?.plan);
  const hasLocked = useMemo(() => items.some((c) => c.locked), [items]);
  const showPlanPromo = tab !== "mine" && tab !== "requests" && !isPremium && hasLocked;

  const decide = (requestId, approve) => {
    decideMutation.mutate(
      { requestId, approve },
      {
        onSuccess: () => toast.success(approve ? t("photo_request_approved") : t("photo_request_rejected")),
        onError: () => toast.error(t("error_generic")),
      }
    );
  };

  const selectTab = useCallback((k) => {
    setTab(k);
    if (k === "mine") {
      setSearchParams({}, { replace: true });
    } else {
      setSearchParams({ tab: k }, { replace: true });
    }
  }, [setSearchParams]);

  return (
    <div className="px-4 md:px-8 pt-6">
      <h1 className="font-heading text-3xl md:text-4xl font-semibold tracking-tight mb-4">{t("liked")}</h1>
      <div className="flex gap-1 mb-4 overflow-x-auto no-scrollbar -mx-4 px-4">
        {TABS.filter((x) => x.k !== "requests" || photoRequests.length > 0 || tab === "requests").map((x) => (
          <button
            key={x.k}
            data-testid={`saved-tab-${x.k}`}
            onClick={() => selectTab(x.k)}
            className={`whitespace-nowrap rounded-full px-3 py-1.5 text-xs border transition inline-flex items-center gap-1.5 ${
              tab === x.k ? "bg-foreground text-background border-foreground" : "bg-card border-border"
            }`}
          >
            {t(x.labelKey)}
            {x.k === "requests" && photoRequests.length > 0 && (
              <span className="rounded-full bg-primary text-white text-[10px] font-bold px-1.5 min-w-[18px] text-center">{photoRequests.length}</span>
            )}
          </button>
        ))}
      </div>

      {showPlanPromo && (
        <button
          type="button"
          onClick={buyPremium}
          disabled={buying}
          data-testid="saved-plan-promo"
          className="mb-4 w-full text-left flex items-center justify-between gap-3 rounded-3xl bg-gradient-to-r from-ink to-zinc-800 text-white p-4 hover:-translate-y-0.5 active:scale-[0.98] transition-transform disabled:opacity-60"
        >
          <div className="min-w-0">
            <p className="font-heading text-base font-semibold flex items-center gap-1.5"><Crown className="w-4 h-4 text-gold" /> {t("who_viewed_unlock_hint")}</p>
            <p className="text-xs text-white/70 mt-0.5">{t("premium")} · {UNLOCK_PRICE.toLocaleString()} {t("sum")}{t("plan_per_month")}</p>
          </div>
          <span className="shrink-0 rounded-full bg-white text-ink text-xs font-semibold px-3.5 py-2">{t("plan_choose_cta")}</span>
        </button>
      )}

      {/* Incoming photo-permission requests: WHO is asking, clearly, with
          approve/reject right on the card. */}
      {tab === "requests" && (
        <div className="space-y-3" data-testid="photo-requests-list">
          {photoRequests.length === 0 && (
            <EmptyState icon={<Camera className="w-6 h-6" />} title={t("photo_requests_empty_title")} hint={t("photo_requests_empty_hint")} />
          )}
          {photoRequests.map(({ request, requester }) => (
            <div key={request.id} className="rounded-3xl bg-card border border-border p-4" data-testid={`photo-request-${request.id}`}>
              <Link to={`/candidate/${requester.id}`} className="flex items-center gap-3">
                {requester.photo_url ? (
                  <img loading="lazy" decoding="async" src={photoSrc(requester.photo_url)} alt="" className="w-12 h-12 rounded-2xl object-cover" />
                ) : (
                  <div className="w-12 h-12 rounded-2xl bg-muted grid place-items-center text-lg font-semibold">{(requester.name || "?")[0]}</div>
                )}
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold truncate">{requester.name}, {requester.age}</p>
                  <p className="text-[11px] text-muted-foreground truncate">{requester.region}{requester.profession ? ` · ${requester.profession}` : ""}</p>
                  <p className="text-[11px] text-muted-foreground mt-0.5">{t("photo_request_line")}</p>
                </div>
              </Link>
              <div className="mt-3 grid grid-cols-2 gap-2">
                <button
                  data-testid={`photo-approve-${request.id}`}
                  onClick={() => decide(request.id, true)}
                  disabled={decideMutation.isPending}
                  className="rounded-2xl bg-primary text-white text-sm font-medium py-2.5 disabled:opacity-50 inline-flex items-center justify-center gap-1.5"
                >
                  <Check className="w-4 h-4" /> {t("photo_request_allow")}
                </button>
                <button
                  data-testid={`photo-reject-${request.id}`}
                  onClick={() => decide(request.id, false)}
                  disabled={decideMutation.isPending}
                  className="rounded-2xl bg-muted text-sm font-medium py-2.5 disabled:opacity-50 inline-flex items-center justify-center gap-1.5"
                >
                  <X className="w-4 h-4" /> {t("photo_request_deny")}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {tab !== "requests" && isLoading && tab === "interested" && (
        <div className="space-y-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-24 rounded-3xl bg-muted animate-pulse" />
          ))}
        </div>
      )}
      {tab !== "requests" && isLoading && tab !== "interested" && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="aspect-[4/5] rounded-3xl bg-muted animate-pulse" />
          ))}
        </div>
      )}
      {tab !== "requests" && !isLoading && items.length === 0 && (
        <div data-testid="saved-empty">
          <EmptyState icon={<Bookmark className="w-6 h-6" />} title={t("saved_empty_title")} hint={t("saved_empty_hint")} />
        </div>
      )}

      {/* "Kim menga qiziqdi" reads much better as a stacked list — the grid's
          square tiles crammed name/age/region/unlock into too little space. */}
      {tab === "interested" ? (
        <div className="space-y-3 stagger" data-testid="saved-grid">
          {items.map((c, idx) => {
            if (c.locked) {
              return (
                <div
                  key={`locked-${tab}-${idx}`}
                  className="flex items-center gap-3 rounded-3xl bg-card border border-border p-3.5"
                >
                  <div className="shrink-0 w-16 h-16 rounded-2xl bg-gradient-to-b from-muted to-card grid place-items-center">
                    <Lock className="w-5 h-5 text-muted-foreground" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium truncate">{c.name}, {c.age}</p>
                    <p className="text-[11px] text-muted-foreground truncate">{c.region}</p>
                  </div>
                  <button
                    type="button"
                    data-testid="locked-upgrade"
                    onClick={buyPremium}
                    disabled={buying}
                    className="shrink-0 rounded-full bg-foreground text-background text-xs font-medium px-3.5 py-2 disabled:opacity-50"
                  >
                    {t("upgrade")}
                  </button>
                </div>
              );
            }

            const photoLocked = c.photo_unlocked !== true;
            const photoUrl = photoLocked ? null : photoSrc(c.photo_url);

            return (
              <Link
                key={c.id}
                to={`/candidate/${c.id}`}
                data-testid={`saved-card-${c.id}`}
                className="flex items-center gap-3 rounded-3xl bg-card border border-border p-3.5 hover:-translate-y-0.5 active:scale-[0.98] transition-transform"
              >
                <div className="shrink-0 w-16 h-16 rounded-2xl bg-muted overflow-hidden relative">
                  {!photoLocked ? (
                    <PhotoFill src={photoUrl} />
                  ) : (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <Lock className="w-5 h-5 text-muted-foreground" />
                    </div>
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium truncate">{c.name}, {c.age}</p>
                  <p className="text-[11px] text-muted-foreground truncate">{c.region}</p>
                </div>
              </Link>
            );
          })}
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 stagger" data-testid="saved-grid">
          {tab !== "requests" && items.map((c, idx) => {
            if (c.locked) {
              // Age + region stay visible (masked name, locked photo) — a real
              // teaser instead of a blank card, consistent with Me's preview.
              return (
                <div key={`locked-${tab}-${idx}`} className="aspect-[4/5] rounded-3xl bg-card border border-border overflow-hidden relative">
                  <div className="absolute inset-0 bg-gradient-to-b from-muted to-card flex flex-col items-center justify-center text-center p-4">
                    <Lock className="w-6 h-6 text-muted-foreground" />
                    <p className="text-sm font-medium mt-2">{c.name}, {c.age}</p>
                    <p className="text-[11px] text-muted-foreground">{c.region}</p>
                    <button type="button" data-testid="locked-upgrade" onClick={buyPremium} disabled={buying} className="mt-3 text-xs font-medium text-foreground underline disabled:opacity-50">{t("upgrade")}</button>
                  </div>
                </div>
              );
            }

            const photoLocked = c.photo_unlocked !== true;
            const photoUrl = photoLocked ? null : photoSrc(c.photo_url);

            return (
              <Link
                key={c.id}
                to={`/candidate/${c.id}`}
                data-testid={`saved-card-${c.id}`}
                className="block aspect-[4/5] rounded-3xl bg-card border border-border overflow-hidden relative hover:shadow-elevated transition-shadow"
              >
                {!photoLocked ? (
                  <PhotoFill src={photoUrl} />
                ) : (
                  <div className="absolute inset-0 bg-muted flex flex-col items-center justify-center">
                    <Lock className="w-6 h-6 text-muted-foreground" />
                    {photoLocked && (
                      <p className="text-[10px] text-muted-foreground mt-2 px-2 text-center">{t("photo_locked")}</p>
                    )}
                  </div>
                )}
                <div className="absolute inset-0 bg-gradient-to-t from-black/65 via-black/0 to-black/0 pointer-events-none" />
                <div className="absolute bottom-2 left-3 right-3 text-white pointer-events-none">
                  <p className="font-medium text-sm">{c.name}, {c.age}</p>
                  <p className="text-[10px] text-white/85">{c.region}</p>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
