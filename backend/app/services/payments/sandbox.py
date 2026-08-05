import uuid

from app.models import Order, StoreSettings
from app.services.payments.base import BaseGateway, PaymentIntent


class SandboxGateway(BaseGateway):
    """Offline gateway that simulates success/failure for development and tests.

    The frontend renders a payment page and calls the "simulate" endpoint with
    an `approved` flag; real providers would redirect to their hosted checkout
    and use webhooks/redirects instead.
    """

    name = "sandbox"

    async def create_intent(self, order: Order, store: StoreSettings) -> PaymentIntent:
        ref = f"SB-{uuid.uuid4().hex[:16].upper()}"
        payment_url = f"#/pay/order/{order.id}?tx={ref}"
        return PaymentIntent(provider_ref=ref, payment_url=payment_url)

    async def confirm_intent(
        self,
        order: Order,
        store: StoreSettings,
        provider_ref: str,
        approved: bool,
    ) -> tuple[bool, str]:
        if approved:
            return True, "Payment approved by sandbox gateway"
        return False, "Payment declined by sandbox gateway"
