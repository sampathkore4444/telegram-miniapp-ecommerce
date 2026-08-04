"""Unit-price resolution: variants first, then product-level quantity tiers."""
from decimal import Decimal


def _sorted_tiers(price_tiers) -> list[dict]:
    if not price_tiers:
        return []
    cleaned = []
    for t in price_tiers:
        try:
            min_qty = int(t.get("min_quantity", 0))
            price = float(t.get("price", 0))
        except (TypeError, ValueError):
            continue
        if min_qty >= 2 and price > 0:
            cleaned.append({"min_quantity": min_qty, "price": price})
    return sorted(cleaned, key=lambda t: t["min_quantity"])


def unit_price_for(product, variant, qty: int) -> Decimal:
    """Effective per-unit price for a product/variant at a given quantity."""
    base = Decimal(str(variant.price)) if variant is not None and variant.price is not None else Decimal(str(product.price))
    tier = None
    for t in _sorted_tiers(product.price_tiers):
        if qty >= t["min_quantity"]:
            tier = t
        else:
            break
    if tier is not None:
        return Decimal(str(tier["price"]))
    return base


def line_subtotal(product, variant, qty: int) -> Decimal:
    return unit_price_for(product, variant, qty) * qty
