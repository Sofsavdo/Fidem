import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { Link } from "react-router-dom";
import { ArrowLeft, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import UZ_REGIONS from "@/lib/regions";

export default function Settings() {
  const { t, user, refresh } = useApp();
  const [f, setF] = useState({
    age_min: 18, age_max: 60,
    region: "", marital_status: "",
    has_children: null,
    height_min: null, height_max: null,
    weight_min: null, weight_max: null,
    require_verified: false, require_financial: false,
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (user?.message_filters) {
      setF((prev) => ({ ...prev, ...user.message_filters }));
    }
  }, [user]);

  const save = async () => {
    setSaving(true);
    try {
      // Strip nulls and empty strings (backend treats them as 'no constraint')
      const payload = { ...f };
      Object.keys(payload).forEach((k) => {
        if (payload[k] === "" || payload[k] === null) delete payload[k];
      });
      // Required defaults
      payload.age_min = payload.age_min ?? 18;
      payload.age_max = payload.age_max ?? 60;
      payload.require_verified = !!payload.require_verified;
      payload.require_financial = !!payload.require_financial;
      await api.patch("/profile/filters", payload);
      toast.success(t("save"));
      await refresh();
    } catch (e) {
      toast.error("Xato");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="px-4 pt-6 pb-8 space-y-5" data-testid="settings-page">
      <div className="flex items-center gap-3">
        <Link to="/me" className="p-2 rounded-full hover:bg-muted" data-testid="settings-back">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <h1 className="font-heading text-2xl font-semibold tracking-tight">{t("who_can_message_me")}</h1>
      </div>
      <p className="text-sm text-muted-foreground -mt-2">
        <ShieldCheck className="inline w-4 h-4 mr-1 text-secondary" />
        {t("filter_hint")}
      </p>

      <div className="rounded-3xl bg-card border border-border p-5 space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <NumField label={`${t("age")} min`} value={f.age_min} onChange={(v) => setF({ ...f, age_min: v })} testid="set-agemin" />
          <NumField label={`${t("age")} max`} value={f.age_max} onChange={(v) => setF({ ...f, age_max: v })} testid="set-agemax" />
        </div>
        <SelectField label={t("region")} value={f.region || ""} onChange={(v) => setF({ ...f, region: v })} testid="set-region"
          options={[{ value: "", label: "—" }, ...UZ_REGIONS.map((r) => ({ value: r, label: r }))]}
        />
        <SelectField label={t("marital_status")} value={f.marital_status || ""} onChange={(v) => setF({ ...f, marital_status: v })} testid="set-marital"
          options={[
            { value: "", label: "—" },
            { value: "single", label: t("single") },
            { value: "divorced", label: t("divorced") },
            { value: "widowed", label: t("widowed") },
          ]}
        />
        <SelectField label={t("has_children")} value={f.has_children === null ? "" : (f.has_children ? "yes" : "no")} onChange={(v) => setF({ ...f, has_children: v === "" ? null : v === "yes" })} testid="set-children"
          options={[
            { value: "", label: "—" },
            { value: "no", label: t("no") },
            { value: "yes", label: t("yes") },
          ]}
        />
        <div className="grid grid-cols-2 gap-3">
          <NumField label={`${t("height")} min`} value={f.height_min} onChange={(v) => setF({ ...f, height_min: v })} testid="set-hmin" />
          <NumField label={`${t("height")} max`} value={f.height_max} onChange={(v) => setF({ ...f, height_max: v })} testid="set-hmax" />
        </div>

        <Toggle label={`✓ ${t("verified")}`} value={f.require_verified} onChange={(v) => setF({ ...f, require_verified: v })} testid="set-req-verified" />
        <Toggle label={`💎 ${t("financial")}`} value={f.require_financial} onChange={(v) => setF({ ...f, require_financial: v })} testid="set-req-financial" />
      </div>

      <button
        data-testid="settings-save"
        onClick={save}
        disabled={saving}
        className="w-full rounded-2xl bg-primary text-white font-medium py-3.5 hover:-translate-y-0.5 active:scale-[0.98] transition disabled:opacity-50"
      >
        {saving ? "..." : t("save")}
      </button>
    </div>
  );
}

function NumField({ label, value, onChange, testid }) {
  return (
    <label className="block">
      <span className="text-xs uppercase tracking-wider text-muted-foreground">{label}</span>
      <input
        data-testid={testid}
        type="number"
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value ? +e.target.value : null)}
        className="mt-1.5 w-full rounded-2xl border border-border bg-card px-4 py-3 outline-none focus:border-primary"
      />
    </label>
  );
}
function SelectField({ label, value, onChange, options, testid }) {
  return (
    <label className="block">
      <span className="text-xs uppercase tracking-wider text-muted-foreground">{label}</span>
      <select
        data-testid={testid}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1.5 w-full rounded-2xl border border-border bg-card px-4 py-3 outline-none focus:border-primary"
      >
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </label>
  );
}
function Toggle({ label, value, onChange, testid }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm">{label}</span>
      <button
        data-testid={testid}
        onClick={() => onChange(!value)}
        className={`w-11 h-6 rounded-full transition-colors relative ${value ? "bg-secondary" : "bg-border"}`}
      >
        <span className={`absolute top-0.5 ${value ? "left-5" : "left-0.5"} w-5 h-5 rounded-full bg-white shadow transition-all`} />
      </button>
    </div>
  );
}
