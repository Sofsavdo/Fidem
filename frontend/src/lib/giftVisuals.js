// Single source of truth for gift-card gradients - the Gift Shop catalog,
// the in-chat quick-send modal, and a delivered gift's chat bubble must all
// render the exact same premium look for the same item, or a gift stops
// looking like "the thing you saw in the shop" the moment it's sent.
export const GIFT_TIER_GRADIENTS = {
  care: "from-violet-500 to-indigo-600",
  love: "from-primary to-fuchsia-600",
  luxury: "from-gold via-amber-500 to-gold-dark",
};

export const GIFT_PLAN_GRADIENTS = {
  standard: "from-sky-500 to-blue-700",
  premium: "from-fuchsia-500 to-primary",
  vip: "from-gold via-amber-500 to-gold-dark",
};

export const GIFT_PLAN_ICONS = { standard: "⭐", premium: "💎", vip: "👑" };

// `meta` is a gift message's meta blob (or a catalog item) - carries either
// a decorative "tier" or a subscription "plan". Older messages sent before
// tier/plan were included fall back to the "care" gradient rather than
// crashing or rendering blank.
export function giftGradient(meta) {
  if (!meta) return GIFT_TIER_GRADIENTS.care;
  if (meta.category === "plan" || meta.plan) {
    return GIFT_PLAN_GRADIENTS[meta.plan] || GIFT_PLAN_GRADIENTS.standard;
  }
  return GIFT_TIER_GRADIENTS[meta.tier] || GIFT_TIER_GRADIENTS.care;
}
