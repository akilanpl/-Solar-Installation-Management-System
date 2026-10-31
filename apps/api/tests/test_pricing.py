"""Pricing and BOM rules do not touch the database."""

from decimal import Decimal

import pytest
from app.domain.bom import BomLine, apply_cable_adjustment, extra_wire_bundles
from app.domain.catalogue import system_quantities
from app.domain.pricing import price_quote, tax_minor


def _wire() -> BomLine:
    return BomLine(
        component_code="WIRE-BUNDLE",
        description="Wiring bundle (10 m)",
        line_kind="material",
        quantity=2,
        unit="bundle",
        unit_cost_minor=84_000,
        unit_price_minor=120_000,
        sort_order=4,
    )


def test_tax_rounds_half_up():
    assert tax_minor(100, 1800) == 18
    assert tax_minor(1, 1800) == 0
    assert tax_minor(3, 1800) == 1


def test_discount_above_ten_percent_is_rejected():
    with pytest.raises(ValueError):
        price_quote(
            material_cost_minor=70,
            material_total_minor=100,
            installation_total_minor=0,
            discount_minor=11,
            tax_rate_bps=1800,
        )


def test_cable_adjustment_is_explicit():
    assert extra_wire_bundles(Decimal("25")) == 0
    assert extra_wire_bundles(Decimal("25.01")) == 1
    assert extra_wire_bundles(Decimal("35")) == 1
    assert extra_wire_bundles(Decimal("35.01")) == 2
    adjusted = apply_cable_adjustment([_wire()], Decimal("36"))
    assert adjusted[0].quantity == 4
    assert adjusted[0].unit_price_minor == 120_000


def test_off_grid_template_includes_battery_and_controller():
    codes = [code for code, _qty, _kind in system_quantities(3, "off_grid")]
    assert "BAT-1KWH" in codes
    assert "CC-MPPT" in codes
    assert "INV-OFG" in codes
    on_grid = [code for code, _qty, _kind in system_quantities(3, "on_grid")]
    assert "BAT-1KWH" not in on_grid
    assert "INV-ONG" in on_grid
