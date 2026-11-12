// Profile facts are stored as the user entered them (older data is in Uzbek,
// newer religion picks are English keys). This maps the well-known values to the
// viewer's language for DISPLAY only - stored data is never changed, and anything
// unknown is shown as it was written.
const RELIGION = {
  islom: "rel_islam", islam: "rel_islam", "ислам": "rel_islam",
  xristianlik: "rel_christianity", christianity: "rel_christianity", "христианство": "rel_christianity",
  yahudiylik: "rel_judaism", judaism: "rel_judaism", "иудаизм": "rel_judaism",
  buddizm: "rel_buddhism", buddhism: "rel_buddhism", "буддизм": "rel_buddhism",
  hinduizm: "rel_hinduism", hinduism: "rel_hinduism", "индуизм": "rel_hinduism",
  boshqa: "rel_other", other: "rel_other", "другое": "rel_other",
};

const EDUCATION = {
  uz: {}, 
  ru: { oliy: "Высшее", magistr: "Магистратура", bakalavr: "Бакалавриат", "o'rta": "Среднее", "o'rta maxsus": "Среднее специальное", talaba: "Студент" },
  en: { oliy: "Higher", magistr: "Master's", bakalavr: "Bachelor's", "o'rta": "Secondary", "o'rta maxsus": "Vocational", talaba: "Student" },
};

const norm = (v) => String(v || "").trim().toLowerCase().replace(/[‘’ʻ`]/g, "'");

export function religionKey(value) {
  return value ? RELIGION[norm(value)] || "" : "";
}

export function religionLabel(value, t) {
  if (!value) return "—";
  const key = RELIGION[norm(value)];
  return key ? t(key) : value;
}

export function educationLabel(value, lang) {
  if (!value) return "—";
  return (EDUCATION[lang] || {})[norm(value)] || value;
}
