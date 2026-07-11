// Human-readable names for internal codes. Raw identifiers like
// "rank_boost" or "chat_unlock" must never reach a user's (or the admin's)
// eyes — every surface renders through these helpers.

// Payment purposes → i18n keys (purpose_* exists in all three languages).
export function purposeLabel(purpose, t) {
  if (!purpose) return "—";
  const key = `purpose_${purpose}`;
  const label = t(key);
  return label && label !== key ? label : purpose.replace(/_/g, " ");
}

// Admin-only maps (the admin panel is Uzbek).
export const PURPOSE_UZ = {
  premium: "Premium tarif",
  standard: "Standard tarif",
  vip: "VIP tarif",
  chat_unlock: "Suhbatni ochish",
  balance_topup: "Balans to'ldirish",
  gift: "Sovg'a",
  concierge: "Concierge xizmati",
  rank_boost: "Saxiylar reytingi hissasi",
  boost: "Profil boost (24 soat)",
};

export const REF_TYPE_UZ = {
  signup_free: "Ro'yxatdan o'tish bonusi",
  paid_subscription: "Pullik tarif (50%)",
  multi_level_2: "2-daraja bonus",
};

export const VERIF_KIND_UZ = {
  selfie: "Selfi tasdiqlash",
  identity: "Shaxsni tasdiqlash (ID)",
  financial: "Moliyaviy tasdiqlash",
};

export const PAY_STATUS_UZ = {
  success: "CLICK orqali to'landi",
  paid: "Balansdan to'landi",
  pending: "Kutilmoqda",
  expired: "Muddati o'tdi",
  failed: "Muvaffaqiyatsiz",
};
