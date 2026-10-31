"""Deterministic bill of materials.

Template quantities are copied from the selected package version. The only
measurement adjustment is extra wiring:

- The template's wiring bundles already cover the first 25 metres.
- Each further 10 metres, rounded up, adds one wiring bundle.
- The added bundles use the same unit cost and customer price as the wiring
  line already on that template version.
- A template with no wiring line is not given a guessed wiring price.

Off-grid batteries and charge controllers come from the off-grid template.
They are not inferred from a survey note.
"""

from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal

INCLUDED_CABLE_M = Decimal("25")
BUNDLE_M = Decimal("10")
WIRING_CODE = "WIRE-BUNDLE"


@dataclass(frozen=True)
class BomLine:
    component_code: str
    description: str
    line_kind: str
    quantity: int
    unit: str
    unit_cost_minor: int
    unit_price_minor: int
    sort_order: int


def extra_wire_bundles(cable_distance_m: Decimal) -> int:
    if cable_distance_m < 0:
        raise ValueError("Cable distance cannot be negative.")
    if cable_distance_m <= INCLUDED_CABLE_M:
        return 0
    extra = cable_distance_m - INCLUDED_CABLE_M
    return int((extra / BUNDLE_M).to_integral_value(rounding=ROUND_CEILING))


def apply_cable_adjustment(lines: list[BomLine], cable_distance_m: Decimal) -> list[BomLine]:
    extra = extra_wire_bundles(cable_distance_m)
    if extra == 0:
        return list(lines)
    adjusted: list[BomLine] = []
    for line in lines:
        if line.component_code == WIRING_CODE:
            adjusted.append(
                BomLine(
                    component_code=line.component_code,
                    description=line.description,
                    line_kind=line.line_kind,
                    quantity=line.quantity + extra,
                    unit=line.unit,
                    unit_cost_minor=line.unit_cost_minor,
                    unit_price_minor=line.unit_price_minor,
                    sort_order=line.sort_order,
                )
            )
        else:
            adjusted.append(line)
    return adjusted
