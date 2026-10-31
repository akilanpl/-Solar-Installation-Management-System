"""Integer-paise pricing.

Tax uses SOLAROPS_GST_RATE_BPS. The default 1800 (18.00%) is a demonstration
rate for this hackathon build. It is not a claim about the statutory rate
that applies to a real invoice. Half-up rounding for a non-negative taxable
amount is `(taxable * bps + 5000) // 10000`.
"""

from dataclasses import dataclass

MAX_DISCOUNT_BPS = 1000


@dataclass(frozen=True)
class PricedQuote:
    material_cost_minor: int
    material_total_minor: int
    installation_total_minor: int
    discount_minor: int
    tax_minor: int
    tax_rate_bps: int
    total_minor: int


def tax_minor(taxable_minor: int, rate_bps: int) -> int:
    if taxable_minor < 0:
        raise ValueError("Taxable amount cannot be negative.")
    if rate_bps < 0 or rate_bps > 2800:
        raise ValueError("Demonstration tax rate is out of the allowed range.")
    return (taxable_minor * rate_bps + 5_000) // 10_000


def maximum_discount_minor(subtotal_minor: int) -> int:
    if subtotal_minor < 0:
        raise ValueError("Subtotal cannot be negative.")
    return subtotal_minor * MAX_DISCOUNT_BPS // 10_000


def price_quote(
    *,
    material_cost_minor: int,
    material_total_minor: int,
    installation_total_minor: int,
    discount_minor: int,
    tax_rate_bps: int,
) -> PricedQuote:
    subtotal = material_total_minor + installation_total_minor
    if discount_minor < 0 or discount_minor > maximum_discount_minor(subtotal):
        raise ValueError("Discount exceeds the authorised 10% of materials plus installation.")
    taxable = subtotal - discount_minor
    tax = tax_minor(taxable, tax_rate_bps)
    return PricedQuote(
        material_cost_minor=material_cost_minor,
        material_total_minor=material_total_minor,
        installation_total_minor=installation_total_minor,
        discount_minor=discount_minor,
        tax_minor=tax,
        tax_rate_bps=tax_rate_bps,
        total_minor=taxable + tax,
    )


def advance_minor(total_minor: int, percent: int) -> int:
    if percent < 1 or percent > 100:
        raise ValueError("Advance percent must be between 1 and 100.")
    return total_minor * percent // 100
