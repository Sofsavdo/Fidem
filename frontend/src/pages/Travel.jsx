import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { toast } from "sonner";
import { Plane, MapPin, Crown, X, CheckCircle2 } from "lucide-react";

const REGION_KEY_MAP = {
  "Toshkent": "region_toshkent",
  "Samarqand": "region_samarqand",
  "Buxoro": "region_buxoro",
  "Andijon": "region_andijon",
  "Farg'ona": "region_fargona",
  "Namangan": "region_namangan",
  "Qashqadaryo": "region_qashqadaryo",
  "Surxondaryo": "region_surxondaryo",
  "Sirdaryo": "region_sirdaryo",
  "Jizzax": "region_jizzax",
  "Navoiy": "region_navoiy",
  "Xorazm": "region_xorazm",
  "Qoraqalpog'iston": "region_qoraqalpogiston",
};

export default function Travel() {
  const { t, refresh } = useApp();
  const [status, setStatus] = useState(null);
  const [country, setCountry] = useState("UZ");  // Default to Uzbekistan
  const [region, setRegion] = useState("");
  const [city, setCity] = useState("");
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(false);

  const translateRegion = (r) => t(REGION_KEY_MAP[r] || r);

  const load = async () => {
    try {
      const r = await api.get("/travel/status");
      setStatus(r.data);
    } catch (e) { /* ignore */ }
  };

  useEffect(() => { load(); }, []);

  const activate = async () => {
    if (!region) { toast.error(t("select_region")); return; }
    setLoading(true);
    try {
      await api.post("/travel/activate", { country, region, city: region, days });
      toast.success(`✈️ ${t("travel_mode")} — ${translateRegion(region)} (${days})`);
      load();
      refresh && refresh();
    } catch (e) {
      toast.error(t("error"));
    } finally { setLoading(false); }
  };

  const deactivate = async () => {
    try {
      await api.post("/travel/deactivate");
      toast.success(t("deactivate"));
      load();
    } catch (e) { toast.error(t("error")); }
  };

  if (!status) return <div className="p-6 text-muted-foreground">{t("loading")}</div>;

  return (
    <div className="max-w-2xl mx-auto p-4 md:p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-heading font-semibold flex items-center gap-2">
          <Plane className="w-6 h-6 text-secondary" /> {t("travel_mode")}
        </h1>
        <p className="text-sm text-muted-foreground mt-1">{t("travel_desc")}</p>
        <p className="text-xs text-muted-foreground mt-2">{t("travel_uz_only_note")}</p>
      </div>

      {!status.allowed && (
        <div className="rounded-2xl border border-amber-300 bg-amber-50 p-4 flex gap-3">
          <Crown className="w-5 h-5 text-amber-600 shrink-0" />
          <div className="text-sm">
            <p className="font-medium text-amber-900">{t("premium")} / {t("vip")}</p>
            <p className="text-amber-800 mt-1">{t("travel_premium_gate")} <Link to="/premium" className="underline font-medium">{t("upgrade")}</Link></p>
          </div>
        </div>
      )}

      {/* Active status */}
      {status.active && (
        <div className="rounded-3xl border border-emerald-300 bg-emerald-50 p-5">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="w-6 h-6 text-emerald-600 shrink-0" />
            <div className="flex-1">
              <p className="font-medium text-emerald-900">{translateRegion(status.travel_region)}</p>
              <p className="text-xs text-emerald-800 mt-1">{new Date(status.travel_until).toLocaleString()}</p>
              <p className="text-xs text-emerald-700 mt-1">{t("region")}: {translateRegion(status.home_region)}</p>
            </div>
            <button data-testid="travel-deactivate" onClick={deactivate} className="text-emerald-700 hover:text-emerald-900"><X className="w-5 h-5" /></button>
          </div>
        </div>
      )}

      {/* Activate form */}
      <div className="rounded-3xl border border-border bg-card p-5 space-y-3">
        <h2 className="font-semibold flex items-center gap-2"><MapPin className="w-4 h-4" /> {t("select_region")}</h2>
        
        {/* Country field (currently only Uzbekistan) */}
        <div>
          <label className="text-xs text-muted-foreground mb-1 block">{t("country")}</label>
          <select 
            data-testid="travel-country" 
            className="w-full px-4 py-2.5 rounded-xl border border-input bg-background text-sm" 
            value={country} 
            onChange={(e) => setCountry(e.target.value)}
            disabled={true}  // Disabled until global expansion
          >
            {(status.countries || []).map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
          </select>
          <p className="text-xs text-secondary mt-1">🌍 Hozircha asosiy Travel Mode O'zbekiston viloyatlari bilan ishlaydi. Global shaharlar bosqichma-bosqich qo'shiladi.</p>
        </div>

        {/* Region/City field */}
        <select data-testid="travel-region" className="w-full px-4 py-2.5 rounded-xl border border-input bg-background text-sm" value={region} onChange={(e) => setRegion(e.target.value)}>
          <option value="">— {t("select_region")} —</option>
          {(status.regions || []).filter((r) => r !== status.home_region).map((r) => <option key={r} value={r}>{translateRegion(r)}</option>)}
        </select>
        <div>
          <label className="text-xs text-muted-foreground">{t("travel_days")}: {days}</label>
          <input data-testid="travel-days" type="range" min="1" max="30" value={days} onChange={(e) => setDays(parseInt(e.target.value, 10))} className="w-full mt-1" />
          <div className="flex justify-between text-[10px] text-muted-foreground"><span>1</span><span>30</span></div>
        </div>
        <button data-testid="travel-activate" disabled={loading || !status.allowed} onClick={activate} className="w-full py-3 rounded-2xl bg-primary text-white font-medium disabled:opacity-50">
          {loading ? "..." : status.active ? t("update_word") : t("activate")}
        </button>
      </div>
    </div>
  );
}
