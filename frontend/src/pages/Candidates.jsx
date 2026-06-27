import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import CandidateCard from "@/components/CandidateCard";
import { useApp } from "@/contexts/AppContext";
import { Filter, X, SlidersHorizontal } from "lucide-react";
import { toast } from "sonner";

export default function Candidates() {
  const { t, user } = useApp();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showFilter, setShowFilter] = useState(false);
  const [filters, setFilters] = useState({ sort: "match", verified_only: false, financial_only: false });
  const [savedIds, setSavedIds] = useState(new Set());

  const load = async () => {
    setLoading(true);
    try {
      const params = { ...filters };
      const r = await api.get("/candidates", { params });
      setItems(r.data || []);
      const s = await api.get("/saved/mine");
      setSavedIds(new Set((s.data || []).map((x) => x.id)));
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line
  }, [filters.sort, filters.verified_only, filters.financial_only]);

  const onSave = async (c) => {
    try {
      if (savedIds.has(c.id)) {
        await api.delete(`/saved/${c.id}`);
        setSavedIds((s) => { const n = new Set(s); n.delete(c.id); return n; });
      } else {
        await api.post("/saved", { user_id: c.id });
        setSavedIds((s) => new Set(s).add(c.id));
        toast.success("Saqlandi");
      }
    } catch (e) {
      toast.error("Xato");
    }
  };

  return (
    <div className="px-4 pt-6 pb-4">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="font-heading text-3xl font-semibold tracking-tight">{t("candidates")}</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            {items.length} {t("candidates").toLowerCase()}
          </p>
        </div>
        <button
          data-testid="open-filter"
          onClick={() => setShowFilter(true)}
          className="rounded-full bg-card border border-border p-3 hover:bg-muted transition"
        >
          <SlidersHorizontal className="w-4 h-4" />
        </button>
      </div>

      {/* sort pills */}
      <div className="flex gap-2 mb-4 overflow-x-auto no-scrollbar">
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
          ✓ Verified
        </button>
        <button
          data-testid="sort-financial"
          onClick={() => setFilters((f) => ({ ...f, financial_only: !f.financial_only }))}
          className={`rounded-full px-3 py-1.5 text-xs whitespace-nowrap border transition ${
            filters.financial_only ? "bg-gold text-ink border-gold" : "bg-card border-border"
          }`}
        >
          💎 Financial
        </button>
      </div>

      {loading ? (
        <div className="grid grid-cols-2 gap-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="aspect-[4/5] rounded-3xl bg-muted animate-pulse" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground" data-testid="no-candidates">
          {t("no_data")}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3 stagger" data-testid="candidates-grid">
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
  const { t } = useApp();
  const [local, setLocal] = useState(filters);
  return (
    <div className="fixed inset-0 z-50 flex items-end" data-testid="filter-sheet">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative w-full max-w-md mx-auto bg-card rounded-t-3xl p-6 max-h-[80vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-heading text-xl font-semibold">{t("filter")}</h3>
          <button data-testid="close-filter" onClick={onClose} className="p-2 rounded-full hover:bg-muted">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="space-y-4">
          <label className="block">
            <span className="text-xs uppercase tracking-wider text-muted-foreground">{t("region")}</span>
            <input
              data-testid="filter-region"
              className="mt-1.5 w-full rounded-2xl border border-border bg-card px-4 py-3"
              placeholder="Toshkent..."
              value={local.region || ""}
              onChange={(e) => setLocal({ ...local, region: e.target.value })}
            />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className="text-xs uppercase tracking-wider text-muted-foreground">{t("age")} min</span>
              <input data-testid="filter-agemin" type="number" className="mt-1.5 w-full rounded-2xl border border-border bg-card px-4 py-3" value={local.age_min || ""} onChange={(e) => setLocal({ ...local, age_min: +e.target.value })} />
            </label>
            <label className="block">
              <span className="text-xs uppercase tracking-wider text-muted-foreground">{t("age")} max</span>
              <input data-testid="filter-agemax" type="number" className="mt-1.5 w-full rounded-2xl border border-border bg-card px-4 py-3" value={local.age_max || ""} onChange={(e) => setLocal({ ...local, age_max: +e.target.value })} />
            </label>
          </div>
          <div className="flex gap-3 pt-2">
            <button data-testid="filter-reset" onClick={() => { setLocal({ sort: "match" }); setFilters({ sort: "match" }); onClose(); }} className="flex-1 rounded-2xl border border-border py-3 hover:bg-muted">{t("reset")}</button>
            <button data-testid="filter-apply" onClick={() => { setFilters(local); onClose(); }} className="flex-1 rounded-2xl bg-primary text-white py-3 font-medium">{t("apply")}</button>
          </div>
        </div>
      </div>
    </div>
  );
}
