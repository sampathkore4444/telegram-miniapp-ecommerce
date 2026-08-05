from abc import ABC, abstractmethod

from app.models import Order, StoreSettings


class PaymentIntent:
    """What the caller needs to hand the buyer to complete a payment."""

    def __init__(
        self,
        provider_ref: str,
        payment_url: str | None = None,
        raw: dict | None = None,
    ) -> None:
        self.provider_ref = provider_ref
        self.payment_url = payment_url
        self.raw = raw or {}


class BaseGateway(ABC):
    """Interface every payment provider must implement."""

    name: str = "base"

    @abstractmethod
    async def create_intent(
        self, order: Order, store: StoreSettings
    ) -> PaymentIntent:
        """Create a new payment intent for an order and return its reference."""

    @abstractmethod
    async def confirm_intent(
        self,
        order: Order,
        store: StoreSettings,
        provider_ref: str,
        approved: bool,
    ) -> tuple[bool, str]:
        """Resolve a pending intent.

        Returns (success, message). Success means the money moved and the order
        should be marked paid; failure means the order is rejected/refunded.
        """
