import React, { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import api from "@/lib/api";
import { useApp } from "@/contexts/AppContext";
import { toast } from "sonner";
import PhotoUpload from "@/components/PhotoUpload";
import WheelDatePicker from "@/components/WheelDatePicker";
import CountrySelect from "@/components/CountrySelect";
import RegionSelect from "@/components/RegionSelect";
import { ChevronLeft, ChevronRight, Check, Sparkles } from "lucide-react";

const STEPS = 7;

const STEP_TITLES = {
  uz: ["Ism va jins", "Manzil", "Oilaviy holat", "Tana ko'rsatkichlari", "Kasb va odat", "Qidiruv afzalliklari", "Profil rasmi"],
  ru: ["Имя и пол", "Адрес", "Семейное положение", "Параметры", "Профессия и привычки", "Поисковые предпочтения", "Фото профиля"],
  en: ["Name & gender", "Location", "Marital status", "Body metrics", "Profession & habits", "Search preferences", "Profile photo"],
};

export default function Onboarding() {
  const { user, t, refresh, lang } = useApp();
  const nav = useNavigate();
  const [searchParams] = useSearchParams();
  // "Complete your profile" (from Me) reuses this screen's data model, but
  // only to fill in whatever is still missing - see the isEdit branch below,
  // which renders a short form of just the empty fields instead of the full
  // wizard. Letting people re-edit info they already gave (name, region,
  // marital status, ...) would undermine trust in what other users already
  // matched/verified against, so already-filled fields are never shown here.
  const isEdit = searchParams.get("edit") === "1" && !!user?.onboarded;
  const [step, setStep] = useState(0);
  const [photoStatus, setPhotoStatus] = useState({ state: "idle", code: "", reason: "" });
  const [submitting, setSubmitting] = useState(false);
  // Prefill from the existing profile so this screen doubles as a safe
  // "edit / complete profile" flow (reached from Me) without wiping fields.
  const [data, setData] = useState({
    name: user?.name || "",
    gender: user?.gender || "male",
    birth_date: user?.birth_date || "2000-01-01",
    country: user?.country || "",
    region: user?.region || "",
    district: user?.district || "",
    marital_status: user?.marital_status || "single",
    has_children: user?.has_children ?? false,
    children_count: user?.children_count || 0,
    height_cm: user?.height_cm || 170,
    weight_kg: user?.weight_kg || 70,
    education: user?.education || "",
    profession: user?.profession || "",
    religion: user?.religion || "",
    looking_for: user?.looking_for || "",
    search_gender: user?.search_gender || "female",
    search_age_min: user?.search_age_min || 20,
    search_age_max: user?.search_age_max || 35,
    search_country: user?.search_country || "",
    search_region: user?.search_region || "",
    photo_url: user?.photo_url || "",
    bio: user?.bio || "",
    smoking: user?.smoking || "no",
    alcohol: user?.alcohol || "no",
    relocation: user?.relocation ?? false,
  });

  const set = (patch) => setData((d) => ({ ...d, ...patch }));

  // Same "empty" rule the backend uses for completeness (services.py
  // PROFILE_FIELDS): booleans always count as answered, everything else is
  // missing if null/undefined/""/0. Restricted to the free-text/descriptive
  // fields that are actually skippable at first onboarding - identity fields
  // (name, gender, birth date, country, marital status, ...) always get a
  // default value up front, so they never legitimately show up here.
  const isFieldEmpty = (v) => (typeof v === "boolean" ? false : v === null || v === undefined || v === "" || v === 0);
  const EDITABLE_MISSING_FIELDS = ["region", "district", "education", "profession", "religion", "looking_for", "bio", "search_region"];
  const missingKeys = isEdit ? EDITABLE_MISSING_FIELDS.filter((k) => isFieldEmpty(user?.[k])) : [];

  const buildPayload = (d) => {
    const payload = { ...d };
    if (!payload.search_gender) payload.search_gender = payload.gender === "male" ? "female" : "male";
    if (!payload.search_country) payload.search_country = payload.country;
    // backend OnboardingProfile requires non-empty string for region / education / religion / search_region
    payload.region = payload.region || "";
    payload.search_region = payload.search_region || "";
    payload.education = payload.education || "";
    payload.religion = payload.religion || "";
    payload.profession = payload.profession || "";
    payload.looking_for = payload.looking_for || "";
    return payload;
  };

  const [savingEdit, setSavingEdit] = useState(false);
  const saveMissingFields = async () => {
    if (savingEdit) return;
    setSavingEdit(true);
    try {
      await api.post("/profile/onboard", buildPayload(data));
      toast.success(t("save"));
      await refresh();
      nav("/me", { replace: true });
    } catch {
      toast.error(t("error"));
    } finally {
      setSavingEdit(false);
    }
  };

  const verifyPhoto = async (url) => {
    if (!url) return;
    setPhotoStatus({ state: "verifying", code: "", reason: "" });
    try {
      const r = await api.post("/face/verify", { photo_url: url });
      const code = r.data?.code || "other";
      if (r.data?.valid) {
        setPhotoStatus({ state: "ok", code: "ok", reason: "" });
      } else if (code === "verification_unavailable") {
        // AI verification itself is down (rate limit/outage), not a problem
        // with the photo - don't block onboarding on a third-party hiccup.
        // Matches the backend's /profile/onboard, which also lets this
        // specific code through unverified instead of rejecting.
        setPhotoStatus({ state: "unavailable", code, reason: r.data?.reason || "" });
      } else {
        const key = `photo_invalid_${code}`;
        const localized = t(key);
        const reason = localized && localized !== key ? localized : (r.data?.reason || t("photo_invalid"));
        setPhotoStatus({ state: "invalid", code, reason });
      }
    } catch {
      setPhotoStatus({ state: "ok", code: "ok", reason: "" });
    }
  };

  const submit = async () => {
    if (submitting) return;
    setSubmitting(true);
    try {
      await api.post("/profile/onboard", buildPayload(data));
      toast.success(t("onboard_complete"));
      // Let the brand-new user actually see their first candidates screen
      // before DailyCheckIn's gamification modal covers it - it fires on
      // any page mount once/day, which without this would stack directly
      // on top of the "profile ready" moment.
      try { sessionStorage.setItem("fidem_just_onboarded", "1"); } catch { /* ignore */ }
      await refresh();
      nav("/", { replace: true });
    } catch (e) {
      const detail = (e.response?.data?.detail || "").toString();
      if (detail === "photo_required") {
        toast.error(t("photo_required"));
        setStep(STEPS - 1);
      } else if (detail.startsWith("photo_invalid:")) {
        const code = detail.split(":")[1] || "other";
        const key = `photo_invalid_${code}`;
        const localized = t(key);
        toast.error(localized && localized !== key ? localized : t("photo_invalid"));
        setPhotoStatus({ state: "invalid", code, reason: localized });
        setStep(STEPS - 1);
      } else {
        toast.error(t("error"));
      }
    } finally {
      setSubmitting(false);
    }
  };

  const next = () => {
    // Step validation
    if (step === 0) {
      if (!data.name?.trim()) { toast.error(t("name_required") || t("name")); return; }
    }
    if (step === 1) {
      if (!data.country) { toast.error(t("country_required") || (t("select_country") || "Select country")); return; }
      // region is only required if the country has a regions list (free-text countries allow blank)
      // We do not strictly enforce here — onboard endpoint accepts empty region for free-text countries.
    }
    if (step === 5) {
      if (!data.search_country) { toast.error(t("country_required") || (t("select_country") || "Select country")); return; }
    }
    if (step === STEPS - 1) {
      if (!data.photo_url) { toast.error(t("photo_required")); return; }
      if (photoStatus.state === "verifying") return;
      if (photoStatus.state === "invalid") { toast.error(photoStatus.reason || t("photo_invalid")); return; }
      submit();
      return;
    }
    setStep((s) => Math.min(STEPS - 1, s + 1));
  };
  const back = () => setStep((s) => Math.max(0, s - 1));

  const stepTitle = (STEP_TITLES[lang] || STEP_TITLES.uz)[step];

  if (isEdit) {
    if (missingKeys.length === 0) {
      nav("/me", { replace: true });
      return null;
    }
    return (
      <div className="relative min-h-[100dvh] bg-background bg-grain overflow-hidden">
        <div className="orb orb-1" style={{ opacity: 0.35 }} />
        <div className="orb orb-2" style={{ opacity: 0.3 }} />
        <div className="relative z-10 max-w-md md:max-w-2xl lg:max-w-3xl mx-auto w-full min-h-[100dvh] flex flex-col px-5 pt-6 pb-28 sm:px-6 md:px-8">
          <button onClick={() => nav("/me")} className="p-2 -ml-2 w-fit rounded-full hover:bg-muted" aria-label="Back" data-testid="ob-edit-back">
            <ChevronLeft className="w-4 h-4" />
          </button>
          <h2 className="mt-3 font-heading text-2xl sm:text-3xl font-semibold tracking-tight leading-tight">{t("complete_profile_cta")}</h2>
          <p className="text-sm text-muted-foreground mt-1">{t("complete_profile_missing_hint")}</p>

          <div className="mt-6 card-premium p-5 sm:p-6 md:p-8" data-testid="onboarding-edit-missing">
            <div className="space-y-5">
              {missingKeys.includes("region") && (
                <Field as="div" label={t("region")}>
                  <RegionSelect testid="ob-edit-region" lang={lang} country={data.country} value={data.region} onChange={(r) => set({ region: r })} placeholder={t("select_region") || "Select region"} />
                </Field>
              )}
              {missingKeys.includes("district") && (
                <Field label={t("district")}>
                  <input data-testid="ob-edit-district" className="input" value={data.district} onChange={(e) => set({ district: e.target.value })} placeholder={t("select_district")} />
                </Field>
              )}
              {missingKeys.includes("education") && (
                <Field label={t("education")}>
                  <input data-testid="ob-edit-education" className="input" value={data.education} onChange={(e) => set({ education: e.target.value })} placeholder={t("education")} />
                </Field>
              )}
              {missingKeys.includes("profession") && (
                <Field label={t("profession")}>
                  <input data-testid="ob-edit-profession" className="input" value={data.profession} onChange={(e) => set({ profession: e.target.value })} placeholder={t("profession")} />
                </Field>
              )}
              {missingKeys.includes("religion") && (
                <Field label={`${t("religion")} (${t("optional") || "optional"})`}>
                  <RadioGroup
                    testid="ob-edit-religion"
                    value={data.religion || "prefer_not_to_say"}
                    onChange={(v) => set({ religion: v === "prefer_not_to_say" ? "" : v })}
                    options={[
                      { value: "prefer_not_to_say", label: t("prefer_not_to_say") || "Prefer not to say" },
                      { value: "Islam", label: t("rel_islam") || "Islam" },
                      { value: "Christianity", label: t("rel_christianity") || "Christianity" },
                      { value: "Judaism", label: t("rel_judaism") || "Judaism" },
                      { value: "Buddhism", label: t("rel_buddhism") || "Buddhism" },
                      { value: "Hinduism", label: t("rel_hinduism") || "Hinduism" },
                      { value: "Other", label: t("rel_other") || "Other" },
                      { value: "None", label: t("rel_none") || "Non-religious" },
                    ]}
                  />
                </Field>
              )}
              {missingKeys.includes("looking_for") && (
                <Field label={t("looking_for")}>
                  <textarea data-testid="ob-edit-lookingfor" rows="3" className="input" value={data.looking_for} onChange={(e) => set({ looking_for: e.target.value })} />
                </Field>
              )}
              {missingKeys.includes("bio") && (
                <Field label={t("bio")}>
                  <textarea data-testid="ob-edit-bio" rows="3" className="input" value={data.bio} onChange={(e) => set({ bio: e.target.value })} />
                </Field>
              )}
              {missingKeys.includes("search_region") && (
                <Field as="div" label={t("search_area")}>
                  <RegionSelect testid="ob-edit-searchregion" lang={lang} country={data.search_country || data.country} value={data.search_region} onChange={(r) => set({ search_region: r })} placeholder={t("select_region") || "Select region"} />
                </Field>
              )}
            </div>
          </div>

          <div className="fixed bottom-0 left-0 right-0 pointer-events-none" style={{ zIndex: 10000 }}>
            <div className="max-w-md md:max-w-2xl lg:max-w-3xl mx-auto px-5 sm:px-6 md:px-8 pb-5 pt-3 pointer-events-auto">
              <button
                data-testid="ob-edit-save"
                onClick={saveMissingFields}
                disabled={savingEdit}
                className="btn-primary w-full"
                style={{ paddingBottom: "max(0.95rem, env(safe-area-inset-bottom))" }}
              >
                {savingEdit ? (
                  <span className="inline-block w-4 h-4 rounded-full border-2 border-white/60 border-t-transparent animate-spin" />
                ) : (
                  <>{t("save")} <Check className="w-4 h-4" /></>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-[100dvh] bg-background bg-grain overflow-hidden">
      <div className="orb orb-1" style={{ opacity: 0.35 }} />
      <div className="orb orb-2" style={{ opacity: 0.3 }} />

      <div className="relative z-10 max-w-md md:max-w-2xl lg:max-w-3xl mx-auto w-full min-h-[100dvh] flex flex-col px-5 pt-6 pb-28 sm:px-6 md:px-8">
        {/* Progress */}
        <div className="flex items-center gap-1.5 mb-6">
          {Array.from({ length: STEPS }).map((_, i) => (
            <div key={i} className={`step-bar ${i <= step ? "active" : ""}`} />
          ))}
        </div>

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <div className="inline-flex items-center gap-1.5 text-[10px] tracking-wider uppercase font-semibold text-foreground bg-primary/10 px-2.5 py-1 rounded-full">
              <Sparkles className="w-3 h-3" /> {`${step + 1} / ${STEPS}`}
            </div>
            <h2 className="mt-3 font-heading text-2xl sm:text-3xl md:text-4xl font-semibold tracking-tight leading-tight">
              {t("onboarding_title")}
            </h2>
            <p className="text-sm md:text-base text-muted-foreground mt-1">{stepTitle}</p>
          </div>
        </div>

        {/* Step card */}
        <div className="mt-6 card-premium p-5 sm:p-6 md:p-8 step-fade" key={step} data-testid={`onboarding-step-${step}`}>
          <div className="space-y-5">
            {step === 0 && (
              <>
                <Field label={t("name")}>
                  <input
                    data-testid="ob-name"
                    className="input"
                    value={data.name}
                    onChange={(e) => set({ name: e.target.value })}
                    placeholder={t("name")}
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
                  <input data-testid="ob-birth" type="hidden" value={data.birth_date} readOnly />
                </Field>
              </>
            )}

            {step === 1 && (
              <>
                <Field as="div" label={t("country")}>
                  <CountrySelect
                    testid="ob-country"
                    lang={lang}
                    value={data.country}
                    onChange={(name) => set({ country: name, region: "", search_country: data.search_country || name, search_region: data.search_country ? data.search_region : "" })}
                    placeholder={t("select_country") || "Select country"}
                  />
                </Field>
                <Field as="div" label={t("region")}>
                  <RegionSelect
                    testid="ob-region"
                    country={data.country}
                    value={data.region}
                    onChange={(r) => set({ region: r, search_region: data.search_country && data.search_country !== data.country ? data.search_region : r })}
                    placeholder={t("select_region") || "Select region"}
                  />
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
                <div className="grid grid-cols-2 gap-3">
                  <Field label={t("height")}><input data-testid="ob-height" type="number" min="140" max="220" className="input" value={data.height_cm} onChange={(e) => set({ height_cm: +e.target.value })} /></Field>
                  <Field label={t("weight")}><input data-testid="ob-weight" type="number" min="35" max="200" className="input" value={data.weight_kg} onChange={(e) => set({ weight_kg: +e.target.value })} /></Field>
                </div>
                <Field label={t("education")}><input data-testid="ob-education" className="input" value={data.education} onChange={(e) => set({ education: e.target.value })} placeholder={t("education")} /></Field>
              </>
            )}

            {step === 4 && (
              <>
                <Field label={t("profession")}><input data-testid="ob-profession" className="input" value={data.profession} onChange={(e) => set({ profession: e.target.value })} placeholder={t("profession")} /></Field>
                <Field label={`${t("religion")} (${t("optional") || "optional"})`}>
                  <RadioGroup
                    testid="ob-religion"
                    value={data.religion || "prefer_not_to_say"}
                    onChange={(v) => set({ religion: v === "prefer_not_to_say" ? "" : v })}
                    options={[
                      { value: "prefer_not_to_say", label: t("prefer_not_to_say") || "Prefer not to say" },
                      { value: "Islam", label: t("rel_islam") || "Islam" },
                      { value: "Christianity", label: t("rel_christianity") || "Christianity" },
                      { value: "Judaism", label: t("rel_judaism") || "Judaism" },
                      { value: "Buddhism", label: t("rel_buddhism") || "Buddhism" },
                      { value: "Hinduism", label: t("rel_hinduism") || "Hinduism" },
                      { value: "Other", label: t("rel_other") || "Other" },
                      { value: "None", label: t("rel_none") || "Non-religious" },
                    ]}
                  />
                </Field>
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
                <Field as="div" label={t("search_area")}>
                  <div className="space-y-2">
                    <CountrySelect
                      testid="ob-searchcountry"
                      lang={lang}
                      value={data.search_country}
                      onChange={(name) => set({ search_country: name, search_region: "" })}
                      placeholder={t("select_country") || "Select country"}
                    />
                    <RegionSelect
                      testid="ob-searchregion"
                      country={data.search_country}
                      value={data.search_region}
                      onChange={(r) => set({ search_region: r })}
                      placeholder={t("select_region") || "Select region"}
                    />
                  </div>
                </Field>
                <div className="grid grid-cols-2 gap-3">
                  <Field label={`${t("age")} min`}><input data-testid="ob-agemin" type="number" min="18" max="80" className="input" value={data.search_age_min} onChange={(e) => set({ search_age_min: +e.target.value })} /></Field>
                  <Field label={`${t("age")} max`}><input data-testid="ob-agemax" type="number" min="18" max="80" className="input" value={data.search_age_max} onChange={(e) => set({ search_age_max: +e.target.value })} /></Field>
                </div>
              </>
            )}

            {step === 6 && (
              <>
                <Field label={`${t("photo")} *`}>
                  <PhotoUpload
                    value={data.photo_url}
                    onChange={(url) => { set({ photo_url: url }); verifyPhoto(url); }}
                    testid="ob-photo"
                  />
                  <p className="text-[11px] text-muted-foreground mt-2">{t("photo_tip")}</p>
                  {photoStatus.state === "verifying" && (
                    <div className="mt-3 rounded-2xl bg-muted/60 border border-border p-3 text-xs flex items-center gap-2" data-testid="ob-photo-verifying">
                      <span className="inline-block w-3 h-3 rounded-full border-2 border-primary border-t-transparent animate-spin" />
                      {t("photo_verifying")}
                    </div>
                  )}
                  {photoStatus.state === "ok" && (
                    <div className="mt-3 rounded-2xl bg-emerald-50 border border-emerald-300 text-emerald-800 p-3 text-xs flex items-center gap-2" data-testid="ob-photo-ok">
                      <Check className="w-3.5 h-3.5" /> {t("photo_verified")}
                    </div>
                  )}
                  {photoStatus.state === "invalid" && (
                    <div className="mt-3 rounded-2xl bg-red-50 border border-red-300 text-red-800 p-3 text-xs" data-testid="ob-photo-invalid">
                      {photoStatus.reason || t("photo_invalid")}
                    </div>
                  )}
                  {photoStatus.state === "unavailable" && (
                    <div className="mt-3 rounded-2xl bg-gold-light/50 border border-gold/40 p-3 text-xs" data-testid="ob-photo-unavailable">
                      {t("photo_verification_pending")}
                    </div>
                  )}
                </Field>
                <Field label={t("bio")}>
                  <textarea data-testid="ob-bio" rows="3" className="input" value={data.bio} onChange={(e) => set({ bio: e.target.value })} />
                </Field>
              </>
            )}
          </div>
        </div>

        {/* Sticky bottom nav */}
        <div className="fixed bottom-0 left-0 right-0 pointer-events-none" style={{ zIndex: 10000 }}>
          <div className="max-w-md md:max-w-2xl lg:max-w-3xl mx-auto px-5 sm:px-6 md:px-8 pb-5 pt-3 pointer-events-auto">
            <div className="flex gap-3 bg-background/85 backdrop-blur-xl rounded-2xl p-2 border border-border shadow-lg" style={{ paddingBottom: "max(0.5rem, env(safe-area-inset-bottom))" }}>
              {step > 0 && (
                <button
                  data-testid="ob-back"
                  onClick={back}
                  className="rounded-xl border border-border bg-card px-4 py-3 hover:bg-muted transition"
                  aria-label="Back"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
              )}
              <button
                data-testid="ob-next"
                onClick={next}
                disabled={submitting || (step === STEPS - 1 && (photoStatus.state === "verifying" || photoStatus.state === "invalid" || !data.photo_url))}
                className="btn-primary flex-1"
                style={{ width: "auto" }}
              >
                {step === STEPS - 1 ? (
                  submitting ? (
                    <span className="inline-block w-4 h-4 rounded-full border-2 border-white/60 border-t-transparent animate-spin" />
                  ) : (
                    <>{t("finish")} <Check className="w-4 h-4" /></>
                  )
                ) : (
                  <>{t("next")} <ChevronRight className="w-4 h-4" /></>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children, as: As = "label" }) {
  return (
    <As className="block">
      <span className="field-label">{label}</span>
      <div className="mt-1.5">{children}</div>
    </As>
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
          className={`chip-option ${value === o.value ? "active" : ""}`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
