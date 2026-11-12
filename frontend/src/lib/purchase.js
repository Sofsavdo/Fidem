// Premium purchase entry point. Every upsell (who liked me, chat paywall,
// filters, privacy...) opens the same quick picker sheet
// (components/PremiumPicker) where the person chooses 1 day / 15 days /
// 1 month and pays without leaving the screen they were on.

export const PICKER_EVENT = "fidem:premium-picker";

// Mirrors backend core.PREMIUM_PERIODS (days -> so'm); the server's numbers
// from /payments/topup-config win when loaded.
export const PREMIUM_PERIODS_DEFAULT = { 1: 9900, 15: 49900, 30: 79000 };

// Kept for screens that show a monthly reference price.
export const PLAN_PRICES = { standard: 34900, premium: PREMIUM_PERIODS_DEFAULT[30], vip: 199000 };

// Tier order used to tell whether a plan is already covered by the user's
// current one (VIP includes Premium includes Standard).
export const PLAN_RANK = { free: 0, standard: 1, premium: 2, vip: 3 };

/**
 * Open the Premium picker. opts: { onPaid, source, reason } - onPaid runs
 * after an instant balance-funded activation (a card payment is followed by
 * the pay sheet, which refreshes the account itself).
 */
export function purchasePlan(plan = "premium", { onPaid, source, reason } = {}) {
  window.dispatchEvent(new CustomEvent(PICKER_EVENT, { detail: { plan, onPaid, source, reason } }));
  return true;
}
