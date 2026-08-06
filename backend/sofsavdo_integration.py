"""Reports a Fidem conversion back to Sofsavdo when the paying user arrived via a
Sofsavdo creator's Flow link (see routers/payments_r.py's process_completed_payment,
the only caller). Fire-and-forget by design: any failure here is logged and
swallowed, never allowed to affect a payment that has already succeeded by the
time this runs. Mirrors Sofsavdo's own src/fidem-integration/fidem-click-token.util.ts
exactly - SOFSAVDO_INTEGRATION_SECRET must be the same value configured there as
FIDEM_INTEGRATION_SECRET.
"""
import hashlib
import hmac
import logging
import os
from datetime import datetime, timezone

import httpx

log = logging.getLogger("fidem.sofsavdo_integration")

SOFSAVDO_WEBHOOK_URL = os.environ.get("SOFSAVDO_WEBHOOK_URL", "https://api.sofsavdo.com/integrations/fidem/webhook")
SOFSAVDO_INTEGRATION_SECRET = os.environ.get("SOFSAVDO_INTEGRATION_SECRET", "")


def _sign(click_token: str, external_payment_id: str, amount_minor: int, commission_amount_minor: int, occurred_at: str) -> str:
    payload = f"{click_token}.{external_payment_id}.{amount_minor}.{commission_amount_minor}.{occurred_at}"
    # Matches signFidemWebhookPayload on the Sofsavdo side exactly: HMAC-SHA256, first 16 hex chars.
    return hmac.new(SOFSAVDO_INTEGRATION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]


async def report_sofsavdo_conversion(click_token: str, external_payment_id: str, amount_som: int, reward_som: int, plan_name: str) -> None:
    """amount_som/reward_som are Fidem's own so'm amounts (whole-number major units) -
    converted to Sofsavdo's minor-unit (tiyin) convention here, the one point the two
    systems' money representations meet. reward_som is Fidem's own already-computed
    referral reward (50% of the payment, tier-capped - see payments_r.py's caller),
    not something Sofsavdo re-derives from a generic commission rate."""
    if not SOFSAVDO_INTEGRATION_SECRET:
        log.warning("SOFSAVDO_INTEGRATION_SECRET not set - skipping conversion report for %s", external_payment_id)
        return

    occurred_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    amount_minor = amount_som * 100
    commission_amount_minor = reward_som * 100
    signature = _sign(click_token, external_payment_id, amount_minor, commission_amount_minor, occurred_at)

    body = {
        "clickToken": click_token,
        "externalPaymentId": external_payment_id,
        "amountMinor": amount_minor,
        "commissionAmountMinor": commission_amount_minor,
        "currency": "UZS",
        "occurredAt": occurred_at,
        "planName": plan_name,
        "signature": signature,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(SOFSAVDO_WEBHOOK_URL, json=body)
            if resp.status_code >= 400:
                log.warning("Sofsavdo conversion webhook returned %s for %s: %s", resp.status_code, external_payment_id, resp.text[:300])
    except Exception as e:
        log.warning("Sofsavdo conversion webhook failed for %s: %s", external_payment_id, e)
