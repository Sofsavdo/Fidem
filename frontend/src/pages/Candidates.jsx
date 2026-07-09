import React, { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import CandidateCard from "@/components/CandidateCard";
import { useApp } from "@/contexts/AppContext";
import { X, SlidersHorizontal, MapPin, Lock } from "lucide-react";
import { toast } from "sonner";
import CountrySelect from "@/components/CountrySelect";
import RegionSelect from "@/components/RegionSelect";
import { useCandidates, useSaved, useToggleSave } from "@/hooks/queries";
import { MATCH_EVENT } from "@/components/MatchCelebration";
import { tapMedium } from "@/lib/haptics";
import { EmptyState } from "@/components/kit";

export default function Candidates() {
  const { t } = useApp();
  const [showFilter, setShowFilter] = useState(false);
  const [filters, setFilters] = useState({ sort: "match", verified_only: false, financial_only: false });

  const { data: items = [], isLoading } = useCandidates(filters);
  const { data: savedList = [] } = useSaved("mine");
  const savedIds = useMemo(() => new Set(savedList.map((x) => x.id)), [savedList]);

  const toggleSave = useToggleSave();

  const onSave = (c) => {
    const isSaved = savedIds.has(c.id);
    tapMedium();
    toggleSave.mutate(
      { candidate: c, isSaved },
      {
        onSuccess: (data) => {
          if (isSaved) return;
          if (data?.mutual_match) {
            window.dispatchEvent(new CustomEvent(MATCH_EVENT, { detail: c }));
          } else {
            toast.success(t("saved_short"));
          }
        },
        onError: () => toast.error(t("error")),
      }
    );
  };

  return (
    <div className="px-4 md:px-8 pt-6 pb-4">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="font-heading text-3xl md:text-4xl font-semibold tracking-tight">{t("candidates")}</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            {items.length} {t("candidates").toLowerCase()}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            data-testid="open-filter"
            onClick={() => setShowFilter(true)}
            className="rounded-full bg-card border border-border p-3 hover:bg-muted transition"
          >
            <SlidersHorizontal className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* sort pills */}
      <div className="flex gap-2 mb-3 overflow-x-auto no-scrollbar">
        {["match", "active", "new"].map((s) => (
          <button
            key={s}
            data-testid={`sort-${s}`}
            onClick={() => setFilters((f) => ({ ...f, sort: s }))}
            className={`rounded-full px-3 py-1.5 text-xs whitespace-nowrap border transition ${
              filters.sort === s
                ? "bg-foreground text-background border-foreground"
                : "bg-card border-border"
            }`}
          >
            {t(`sort_${s}`)}
          </button>
        ))}
        <button
          data-testid="sort-verified"
          onClick={() => setFilters((f) => ({ ...f, verified_only: !f.verified_only }))}
          className={`rounded-full px-3 py-1.5 text-xs whitespace-nowrap border transition ${
            filters.verified_only ? "bg-secondary text-white border-secondary" : "bg-card border-border"
          }`}
        >
          ✓ {t("only_verified")}
        </button>
        <button
          data-testid="sort-financial"
          onClick={() => setFilters((f) => ({ ...f, financial_only: !f.financial_only }))}
          className={`rounded-full px-3 py-1.5 text-xs whitespace-nowrap border transition ${
            filters.financial_only ? "bg-gold text-ink border-gold" : "bg-card border-border"
          }`}
        >
          💎 {t("only_financial")}
        </button>
      </div>

      {/* Active filter chips */}
      {(filters.country || filters.region || filters.district || filters.age_min || filters.age_max) && (
        <div className="flex flex-wrap gap-1.5 mb-3" data-testid="active-filter-chips">
          {filters.country && (
            <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 text-foreground px-2.5 py-1 text-[11px] font-medium">
              <MapPin className="w-3 h-3" /> {filters.country}
              <button onClick={() => setFilters((f) => ({ ...f, country: undefined, region: undefined }))} className="ml-0.5 hover:opacity-70" data-testid="chip-clear-country"><X className="w-3 h-3" /></button>
            </span>
          )}
          {filters.region && (
            <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 text-foreground px-2.5 py-1 text-[11px] font-medium">
              <MapPin className="w-3 h-3" /> {filters.region}
              <button onClick={() => setFilters((f) => ({ ...f, region: undefined }))} className="ml-0.5 hover:opacity-70" data-testid="chip-clear-region"><X className="w-3 h-3" /></button>
            </span>
          )}
          {filters.district && (
            <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 text-foreground px-2.5 py-1 text-[11px] font-medium">
              {filters.district}
              <button onClick={() => setFilters((f) => ({ ...f, district: undefined }))} className="ml-0.5 hover:opacity-70" data-testid="chip-clear-district"><X className="w-3 h-3" /></button>
            </span>
          )}
          {(filters.age_min || filters.age_max) && (
            <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 text-foreground px-2.5 py-1 text-[11px] font-medium">
              {filters.age_min || 18}–{filters.age_max || 80} {t("age").toLowerCase()}
              <button onClick={() => setFilters((f) => ({ ...f, age_min: undefined, age_max: undefined }))} className="ml-0.5 hover:opacity-70" data-testid="chip-clear-age"><X className="w-3 h-3" /></button>
            </span>
          )}
        </div>
      )}

      {isLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="aspect-[4/5] rounded-3xl bg-muted animate-pulse" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div data-testid="no-candidates">
          <EmptyState
            icon={<SlidersHorizontal className="w-6 h-6" />}
            title={t("candidates_empty_title")}
            hint={t("candidates_empty_hint")}
            action={
              <button onClick={() => setFilters({ sort: "match" })} className="text-sm font-semibold text-primary">
                {t("reset")}
              </button>
            }
          />
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 stagger" data-testid="candidates-grid">
          {items.map((c) => (
            <CandidateCard key={c.id} c={c} onSave={onSave} saved={savedIds.has(c.id)} />
          ))}
        </div>
      )}

      {showFilter && <FilterSheet filters={filters} setFilters={setFilters} onClose={() => setShowFilter(false)} />}
    </div>
  );
}

function FilterSheet({ filters, setFilters, onClose }) {
  const { t, lang, user } = useApp();
  const isPaid = ["standard", "premium", "vip"].includes(user?.plan);
  const [local, setLocal] = useState(filters);
  return (
    <div className="fixed inset-0 flex items-end" style={{ zIndex: 10001 }} data-testid="filter-sheet">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div
        className="relative w-full max-w-md mx-auto bg-card rounded-t-3xl p-6 max-h-[85vh] overflow-y-auto"
        style={{ paddingBottom: "max(1.5rem, env(safe-area-inset-bottom))" }}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-heading text-xl font-semibold">{t("filter")}</h3>
          <button data-testid="close-filter" onClick={onClose} className="p-2 rounded-full hover:bg-muted">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="space-y-4">
          <label className="block">
            <span className="text-xs uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <MapPin className="w-3.5 h-3.5" /> {t("country")}
            </span>
            <div className="mt-1.5">
              <CountrySelect
                testid="filter-country"
                lang={lang}
                value={local.country || ""}
                onChange={(name) => setLocal({ ...local, country: name || undefined, region: undefined })}
                placeholder={t("select_country") || "Select country"}
              />
            </div>
          </label>
          <label className="block">
            <span className="text-xs uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <MapPin className="w-3.5 h-3.5" /> {t("region")}
            </span>
            <div className="mt-1.5">
              <RegionSelect
                testid="filter-region"
                country={local.country}
                value={local.region || ""}
                onChange={(r) => setLocal({ ...local, region: r || undefined })}
                placeholder={t("select_region") || "Select region"}
              />
            </div>
          </label>
          <label className="block">
            <span className="text-xs uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              {t("district")}
              {!isPaid && <Lock className="w-3 h-3" />}
            </span>
            {isPaid ? (
              <input
                data-testid="filter-district"
                className="mt-1.5 w-full rounded-2xl border border-border bg-card px-4 py-3 outline-none focus:border-primary"
                placeholder={t("select_district")}
                value={local.district || ""}
                onChange={(e) => setLocal({ ...local, district: e.target.value || undefined })}
              />
            ) : (
              <Link
                to="/premium?tab=plans"
                data-testid="filter-district-locked"
                onClick={onClose}
                className="mt-1.5 flex items-center justify-between w-full rounded-2xl border border-dashed border-border bg-muted/30 px-4 py-3 text-sm text-muted-foreground"
              >
                {t("more_filters_premium_hint") || t("upgrade")}
                <Lock className="w-3.5 h-3.5" />
              </Link>
            )}
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className="text-xs uppercase tracking-wider text-muted-foreground">{t("age_min")}</span>
              <input data-testid="filter-agemin" type="number" min="18" max="80" className="mt-1.5 w-full rounded-2xl border border-border bg-card px-4 py-3 outline-none focus:border-primary" value={local.age_min || ""} onChange={(e) => setLocal({ ...local, age_min: e.target.value ? +e.target.value : undefined })} />
            </label>
            <label className="block">
              <span className="text-xs uppercase tracking-wider text-muted-foreground">{t("age_max")}</span>
              <input data-testid="filter-agemax" type="number" min="18" max="80" className="mt-1.5 w-full rounded-2xl border border-border bg-card px-4 py-3 outline-none focus:border-primary" value={local.age_max || ""} onChange={(e) => setLocal({ ...local, age_max: e.target.value ? +e.target.value : undefined })} />
            </label>
          </div>
          <div className="flex gap-3 pt-2">
            <button data-testid="filter-reset" onClick={() => { const reset = { sort: "match" }; setLocal(reset); setFilters(reset); onClose(); }} className="flex-1 rounded-2xl border border-border py-3 hover:bg-muted">{t("reset")}</button>
            <button data-testid="filter-apply" onClick={() => { setFilters(local); onClose(); }} className="flex-1 rounded-2xl bg-primary text-white py-3 font-medium">{t("apply")}</button>
          </div>
        </div>
      </div>
    </div>
  );
}
