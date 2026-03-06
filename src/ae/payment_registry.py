from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .enums import PaymentProvider, PaymentMethod


@dataclass(frozen=True)
class PaymentSpec:
    provider: PaymentProvider
    allowed_methods: List[PaymentMethod]
    requires_external_ref: bool = False


# Code-first registry (v1). Governance + versioning comes later.
REGISTRY: Dict[PaymentProvider, PaymentSpec] = {
    PaymentProvider.manual: PaymentSpec(
        provider=PaymentProvider.manual,
        allowed_methods=[
            PaymentMethod.cash,
            PaymentMethod.bank_transfer,
            PaymentMethod.qr,
            PaymentMethod.other,
        ],
        requires_external_ref=False,
    ),
    PaymentProvider.stripe: PaymentSpec(
        provider=PaymentProvider.stripe,
        allowed_methods=[PaymentMethod.card],
        requires_external_ref=True,
    ),
    PaymentProvider.paypal: PaymentSpec(
        provider=PaymentProvider.paypal,
        allowed_methods=[PaymentMethod.card, PaymentMethod.other],
        requires_external_ref=True,
    ),
    PaymentProvider.other: PaymentSpec(
        provider=PaymentProvider.other,
        allowed_methods=[PaymentMethod.other],
        requires_external_ref=False,
    ),
}


def validate_payment_provider_method(provider: PaymentProvider, method: PaymentMethod) -> None:
    spec = REGISTRY.get(provider)
    if not spec:
        raise ValueError(f"Unknown payment provider: {provider}")
    if method not in spec.allowed_methods:
        raise ValueError(f"Payment method {method} not allowed for provider {provider}")


def validate_external_ref(provider: PaymentProvider, external_ref: Optional[str]) -> None:
    spec = REGISTRY.get(provider)
    if not spec:
        raise ValueError(f"Unknown payment provider: {provider}")
    if spec.requires_external_ref and not (external_ref and str(external_ref).strip()):
        raise ValueError(f"provider {provider} requires external_ref")
