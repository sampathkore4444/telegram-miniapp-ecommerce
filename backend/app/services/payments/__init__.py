"""Pluggable online-payment gateway layer.

The store talks to a `BaseGateway`; real providers (Stripe, TON, ...) can be
added later by implementing the same interface and registering them in
`app/services/payments/factory.py`.
"""
from app.services.payments.base import BaseGateway, PaymentIntent
from app.services.payments.factory import get_gateway, list_gateways

__all__ = ["BaseGateway", "PaymentIntent", "get_gateway", "list_gateways"]
