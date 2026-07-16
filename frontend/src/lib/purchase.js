// One-tap plan activation. Every plan-specific upsell button (privacy
// center, who-viewed promo, profile tier hint, chat paywall, ...) charges
// through here directly instead of dumping the user onto the generic plans
// page — an extra navigation step measurably kills purchase intent.
import api from "@/lib/api";
import { toast } from "sonner";
import { openExternalLink } from "@/lib/telegram";

export const PLAN_PRICES = { standard: 34900, premium: 79000, vip: 199000 };

let inFlight = false;

/**
 * Start a plan purchase immediately (balance-first, CLICK for remainder).
 * opts: { t, navigate, onPaid } — navigate is used for the P2P fallback,
 * onPaid runs after an instant balance-funded activation (refresh user).
 */
export async function purchasePlan(plan, { t, navigate, onPaid } = {}) {
  if (inFlight || !PLAN_PRICES[plan]) return false;
  inFlight = true;
  try {
    const r = await api.post("/payments/create", { purpose: plan, amount: PLAN_PRICES[plan] });
    if (r.data?.status === "paid") {
      toast.success(t ? t("payment_success") : "OK");
      if (onPaid) await onPaid();
      return true;
    }
    if (r.data?.payment_link) {
      openExternalLink(r.data.payment_link);
      if (t) toast.info(t("redirecting_payment"));
      return true;
    }
    return false;
  } catch (e) {
    const detail = (e?.response?.data?.detail || "").toString();
    if (detail === "click_disabled") {
      if (t) toast.info(t("click_disabled_error"));
      if (navigate) navigate("/premium?tab=balance");
    } else if (t) {
      toast.error(t("error_generic"));
    }
    return false;
  } finally {
    inFlight = false;
  }
}
