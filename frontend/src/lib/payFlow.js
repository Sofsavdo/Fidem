// One way to continue after POST /payments/create (or a concierge order):
// a Hamyon payment opens the card-transfer sheet (components/PayTransferSheet),
// an older CLICK payment opens its external page.
import { toast } from "sonner";
import { openExternalLink } from "@/lib/telegram";

export const PAY_EVENT = "fidem:pay";
export const PAID_EVENT = "fidem:paid";

/** Returns true when a payment step was opened for the user. */
export function startPayment(data, t) {
  if (data?.method === "hamyon" && data.card) {
    window.dispatchEvent(new CustomEvent(PAY_EVENT, { detail: data }));
    return true;
  }
  if (data?.payment_link) {
    openExternalLink(data.payment_link);
    if (t) toast.info(t("redirecting_payment"));
    return true;
  }
  return false;
}

/** Error toast text for a failed /payments/create, or "" when the caller handles it. */
export function payErrorText(detail, t) {
  if (detail === "payment_provider_error") return t("pay_provider_error");
  if (detail === "click_min_1000") return t("click_min_error");
  return "";
}

/** Run something after any payment completes (refresh lists, access, ...). */
export function onPaid(fn) {
  const h = (e) => fn(e.detail);
  window.addEventListener(PAID_EVENT, h);
  return () => window.removeEventListener(PAID_EVENT, h);
}
