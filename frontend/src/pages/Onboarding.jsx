import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { toast } from "sonner";
import PhotoUpload from "@/components/PhotoUpload";
import WheelDatePicker from "@/components/WheelDatePicker";
import { ChevronLeft, ChevronRight, Check } from "lucide-react";

const UZ_REGIONS = [
  "Toshkent", "Samarqand", "Buxoro", "Andijon", "Farg'ona", "Namangan",
  "Qashqadaryo", "Surxondaryo", "Sirdaryo", "Jizzax", "Navoiy", "Xorazm", "Qoraqalpog'iston",
];

const STEPS = 7;

export default function Onboarding() {
  const { user, t, refresh } = useApp();
  const nav = useNavigate();
  const [step, setStep] = useState(0);
  const [data, setData] = useState({
    name: user?.name || "",
    gender: "male",
    birth_date: "2000-01-01",
    country: "Uzbekistan",
    region: "Toshkent",
    district: "",
    marital_status: "single",
    has_children: false,
    children_count: 0,
    height_cm: 170,
    weight_kg: 70,
    education: "Oliy",
    profession: "",
    religion: "Islom",
    looking_for: "",
    search_gender: "female",
    search_age_min: 20,
    search_age_max: 35,
    search_region: "Toshkent",
    photo_url: "",
    bio: "",
    smoking: "no",
    alcohol: "no",
    relocation: false,
  });

  const set = (patch) => setData((d) => ({ ...d, ...patch }));

  const submit = async () => {
    try {
      // toggle search_gender opposite by default if user didn't pick
      const payload = { ...data };
      if (!payload.search_gender) payload.search_gender = payload.gender === "male" ? "female" : "male";
      await api.post("/profile/onboard", payload);
      toast.success(t("onboard_complete"));
      await refresh();
      nav("/", { replace: true });
    } catch (e) {
      toast.error(e.response?.data?.detail || "Xato");
    }
  };

  const next = () => {
    if (step === STEPS - 1) submit();
    else setStep((s) => Math.min(STEPS - 1, s + 1));
  };
  const back = () => setStep((s) => Math.max(0, s - 1));

  return (
    <div className="min-h-screen bg-background bg-grain flex flex-col">
      <div className="max-w-md mx-auto w-full flex-1 flex flex-col px-6 pt-10 pb-8">
        {/* progress */}
        <div className="flex items-center gap-1.5 mb-8">
          {Array.from({ length: STEPS }).map((_, i) => (
            <div
              key={i}
              className={`h-1 flex-1 rounded-full transition-colors ${
                i <= step ? "bg-primary" : "bg-border"
              }`}
            />
          ))}
        </div>

        <h2 className="font-heading text-3xl font-semibold tracking-tight">
          {t("onboarding_title")}
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          Qadam {step + 1} / {STEPS}
        </p>

        <div className="mt-8 space-y-4 flex-1" data-testid={`onboarding-step-${step}`}>
          {step === 0 && (
            <>
              <Field label={t("name")}>
                <input
                  data-testid="ob-name"
                  className="input" value={data.name}
                  onChange={(e) => set({ name: e.target.value })}
                />
              </Field>
              <Field label={t("gender")}>
                <RadioGroup
                  testid="ob-gender"
                  value={data.gender}
                  onChange={(v) => set({ gender: v, search_gender: v === "male" ? "female" : "male" })}
                  options={[
                    { value: "male", label: t("male") },
                    { value: "female", label: t("female") },
                  ]}
                />
              </Field>
              <Field label={t("birth_date")}>
                <WheelDatePicker
                  value={data.birth_date}
                  onChange={(iso) => set({ birth_date: iso })}
                />
                {/* Hidden fallback to preserve test_id behavior */}
                <input data-testid="ob-birth" type="hidden" value={data.birth_date} readOnly />
              </Field>
            </>
          )}
          {step === 1 && (
            <>
              <Field label={t("country")}>
                <input data-testid="ob-country" className="input" value={data.country} onChange={(e) => set({ country: e.target.value })} />
              </Field>
              <Field label={t("region")}>
                <div className="grid grid-cols-2 gap-2" data-testid="ob-region-grid">
                  {UZ_REGIONS.map((r) => (
                    <button
                      key={r}
                      type="button"
                      data-testid={`ob-region-${r}`}
                      onClick={() => set({ region: r, search_region: r })}
                      className={`rounded-xl border px-3 py-2.5 text-sm transition ${
                        data.region === r ? "bg-primary text-white border-primary" : "bg-card border-border hover:border-foreground/30"
                      }`}
                    >
                      {r}
                    </button>
                  ))}
                </div>
                <input data-testid="ob-region" type="hidden" value={data.region} readOnly />
              </Field>
              <Field label={t("district")}>
                <input data-testid="ob-district" className="input" value={data.district} onChange={(e) => set({ district: e.target.value })} placeholder={t("select_district")} />
              </Field>
            </>
          )}
          {step === 2 && (
            <>
              <Field label={t("marital_status")}>
                <RadioGroup
                  testid="ob-marital"
                  value={data.marital_status}
                  onChange={(v) => set({ marital_status: v })}
                  options={[
                    { value: "single", label: t("single") },
                    { value: "divorced", label: t("divorced") },
                    { value: "widowed", label: t("widowed") },
                  ]}
                />
              </Field>
              <Field label={t("has_children")}>
                <RadioGroup
                  testid="ob-haschildren"
                  value={data.has_children ? "yes" : "no"}
                  onChange={(v) => set({ has_children: v === "yes", children_count: v === "no" ? 0 : data.children_count })}
                  options={[{ value: "no", label: t("no") }, { value: "yes", label: t("yes") }]}
                />
              </Field>
              {data.has_children && (
                <Field label={t("children_count")}>
                  <input data-testid="ob-childcount" type="number" min="1" max="10" className="input" value={data.children_count} onChange={(e) => set({ children_count: +e.target.value })} />
                </Field>
              )}
            </>
          )}
          {step === 3 && (
            <>
              <Field label={t("height")}><input data-testid="ob-height" type="number" min="140" max="220" className="input" value={data.height_cm} onChange={(e) => set({ height_cm: +e.target.value })} /></Field>
              <Field label={t("weight")}><input data-testid="ob-weight" type="number" min="35" max="200" className="input" value={data.weight_kg} onChange={(e) => set({ weight_kg: +e.target.value })} /></Field>
              <Field label={t("education")}><input data-testid="ob-education" className="input" value={data.education} onChange={(e) => set({ education: e.target.value })} /></Field>
            </>
          )}
          {step === 4 && (
            <>
              <Field label={t("profession")}><input data-testid="ob-profession" className="input" value={data.profession} onChange={(e) => set({ profession: e.target.value })} /></Field>
              <Field label={t("religion")}><input data-testid="ob-religion" className="input" value={data.religion} onChange={(e) => set({ religion: e.target.value })} /></Field>
              <Field label={t("smoking")}>
                <RadioGroup testid="ob-smoking" value={data.smoking} onChange={(v) => set({ smoking: v })}
                  options={[{ value: "no", label: t("no") }, { value: "sometimes", label: t("sometimes") }, { value: "yes", label: t("yes") }]} />
              </Field>
              <Field label={t("alcohol")}>
                <RadioGroup testid="ob-alcohol" value={data.alcohol} onChange={(v) => set({ alcohol: v })}
                  options={[{ value: "no", label: t("no") }, { value: "sometimes", label: t("sometimes") }, { value: "yes", label: t("yes") }]} />
              </Field>
              <Field label={t("relocation")}>
                <RadioGroup testid="ob-relocation" value={data.relocation ? "yes" : "no"} onChange={(v) => set({ relocation: v === "yes" })}
                  options={[{ value: "no", label: t("no") }, { value: "yes", label: t("yes") }]} />
              </Field>
            </>
          )}
          {step === 5 && (
            <>
              <Field label={t("looking_for")}>
                <textarea data-testid="ob-lookingfor" rows="3" className="input" value={data.looking_for} onChange={(e) => set({ looking_for: e.target.value })} />
              </Field>
              <Field label={t("search_area")}>
                <div className="grid grid-cols-2 gap-2">
                  {UZ_REGIONS.map((r) => (
                    <button
                      key={r}
                      type="button"
                      data-testid={`ob-searchregion-${r}`}
                      onClick={() => set({ search_region: r })}
                      className={`rounded-xl border px-3 py-2.5 text-sm transition ${
                        data.search_region === r ? "bg-primary text-white border-primary" : "bg-card border-border hover:border-foreground/30"
                      }`}
                    >
                      {r}
                    </button>
                  ))}
                </div>
                <input data-testid="ob-searchregion" type="hidden" value={data.search_region} readOnly />
              </Field>
              <div className="grid grid-cols-2 gap-3">
                <Field label={`${t("age")} min`}><input data-testid="ob-agemin" type="number" min="18" max="80" className="input" value={data.search_age_min} onChange={(e) => set({ search_age_min: +e.target.value })} /></Field>
                <Field label={`${t("age")} max`}><input data-testid="ob-agemax" type="number" min="18" max="80" className="input" value={data.search_age_max} onChange={(e) => set({ search_age_max: +e.target.value })} /></Field>
              </div>
            </>
          )}
          {step === 6 && (
            <>
              <Field label={t("photo")}>
                <PhotoUpload value={data.photo_url} onChange={(url) => set({ photo_url: url })} testid="ob-photo" />
              </Field>
              <Field label={t("bio")}>
                <textarea data-testid="ob-bio" rows="3" className="input" value={data.bio} onChange={(e) => set({ bio: e.target.value })} />
              </Field>
            </>
          )}
        </div>

        <div className="flex gap-3 pt-4">
          {step > 0 && (
            <button
              data-testid="ob-back"
              onClick={back}
              className="rounded-2xl border border-border px-5 py-3 hover:bg-muted transition"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
          )}
          <button
            data-testid="ob-next"
            onClick={next}
            className="flex-1 rounded-2xl bg-primary text-white font-medium py-3 px-6 inline-flex items-center justify-center gap-2 hover:-translate-y-0.5 active:scale-[0.98] transition"
          >
            {step === STEPS - 1 ? (<>{t("finish")} <Check className="w-4 h-4" /></>) : (<>{t("next")} <ChevronRight className="w-4 h-4" /></>)}
          </button>
        </div>
      </div>

      <style>{`.input { @apply w-full rounded-2xl border border-border bg-card px-4 py-3 outline-none focus:border-primary; }`}</style>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="text-xs uppercase tracking-wider text-muted-foreground">{label}</span>
      <div className="mt-1.5">{children}</div>
    </label>
  );
}

function RadioGroup({ value, onChange, options, testid }) {
  return (
    <div className="flex gap-2 flex-wrap">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          data-testid={`${testid}-${o.value}`}
          onClick={() => onChange(o.value)}
          className={`rounded-full px-4 py-2 text-sm border transition ${
            value === o.value
              ? "bg-primary text-white border-primary"
              : "bg-card border-border hover:border-foreground/30"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
