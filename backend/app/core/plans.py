"""Plan definitions and the single source of truth for plan-gated features.

Plans are stored on the merchant (an admin User) via the ``plan`` column.
Everything a merchant can or cannot do is derived from this catalog; the
frontend only mirrors it cosmetically, the backend enforces it.
"""
import enum

from app.core.errors import PermissionError


class Plan(str, enum.Enum):
    STARTER = "starter"
    GROWTH = "growth"
    PRO = "pro"


# Feature name -> availability per plan.
# - bool features are simply on/off.
# - `products_limit` is an int cap (None = unlimited).
FEATURES: dict[Plan, dict[str, bool | int | None]] = {
    Plan.STARTER: {
        "coupons": False,
        "online_payments": False,
        "analytics": False,
        "multi_store": False,
        "priority_support": False,
        "products_limit": 50,
    },
    Plan.GROWTH: {
        "coupons": True,
        "online_payments": True,
        "analytics": True,
        "multi_store": False,
        "priority_support": False,
        "products_limit": 500,
    },
    Plan.PRO: {
        "coupons": True,
        "online_payments": True,
        "analytics": True,
        "multi_store": True,
        "priority_support": True,
        "products_limit": None,  # unlimited
    },
}

PLAN_NAMES = {
    Plan.STARTER: "Starter",
    Plan.GROWTH: "Growth",
    Plan.PRO: "Pro",
}

# Public feature flag keys exposed to the frontend (booleans only).
PUBLIC_FEATURES = ("coupons", "online_payments", "analytics", "multi_store", "priority_support")


def features_for(plan: Plan) -> dict:
    return FEATURES.get(plan, FEATURES[Plan.STARTER])


def feature_enabled(plan: Plan, feature: str) -> bool:
    return bool(features_for(plan).get(feature))


def plan_limit(plan: Plan, key: str = "products_limit") -> int | None:
    limit = features_for(plan).get(key)
    return limit if isinstance(limit, int) else None


def public_features(plan: Plan) -> dict:
    """Bool flags safe to expose to the client."""
    return {name: feature_enabled(plan, name) for name in PUBLIC_FEATURES}


def ensure_feature(plan: Plan, feature: str, message: str | None = None) -> None:
    """Raise a 403 unless the plan includes ``feature``."""
    if not feature_enabled(plan, feature):
        raise PermissionError(
            message or f"'{feature}' is not available on the {PLAN_NAMES[plan]} plan.",
            code="plan_required",
        )


def ensure_quota(
    plan: Plan,
    current_count: int,
    key: str = "products_limit",
    message: str | None = None,
) -> None:
    """Raise a 403 when ``current_count`` is at/over the plan's limit for ``key``."""
    limit = plan_limit(plan, key)
    if limit is not None and current_count >= limit:
        raise PermissionError(
            message
            or f"Your {PLAN_NAMES[plan]} plan allows up to {limit} products. "
            f"Upgrade to add more.",
            code="plan_limit",
        )
