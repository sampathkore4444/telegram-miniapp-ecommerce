from app.core.config import settings
from app.services.payments.base import BaseGateway
from app.services.payments.sandbox import SandboxGateway

GATEWAYS: dict[str, type[BaseGateway]] = {
    "sandbox": SandboxGateway,
}


def list_gateways() -> list[str]:
    return sorted(GATEWAYS.keys())


def get_gateway(name: str | None = None) -> BaseGateway:
    """Return a gateway instance for `name` (defaults to the configured one)."""
    selected = (name or settings.PAYMENT_GATEWAY or "sandbox").strip().lower()
    cls = GATEWAYS.get(selected)
    if cls is None:
        raise ValueError(f"Unknown payment gateway: {selected}")
    return cls()
