"""Version 1 package templates.

Prices are demonstration catalogue prices in paise, stored on the template
line so a later catalogue edit creates a new version instead of changing a
quotation. Customer price is the stored unit price. Material cost is 70% of
that price, rounded down, and is not a supplier invoice.

A system package uses two 550 W panel lines per kilowatt (the catalogue's
declared quantity, not a site-specific engineering calculation).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import SolarPackage
from app.models.workflow import CatalogueComponent, PackageTemplateLine, PackageTemplateVersion

COMPONENTS: tuple[tuple[str, str, str], ...] = (
    ("PANEL-550", "Solar panel 550 W", "each"),
    ("INV-ONG", "On-grid inverter", "each"),
    ("INV-OFG", "Off-grid inverter", "each"),
    ("BAT-1KWH", "Battery 1 kWh", "each"),
    ("CC-MPPT", "MPPT charge controller", "each"),
    ("STAND", "Panel stand", "each"),
    ("WIRE-BUNDLE", "Wiring bundle (10 m)", "bundle"),
    ("CONN-MC4", "MC4 connector pair", "each"),
    ("SW-DC", "DC isolator switch", "each"),
    ("BOX-AC", "AC distribution box", "each"),
    ("EARTH", "Earthing and safety kit", "kit"),
    ("SVC-INSTALL", "Installation service", "service"),
)

# Customer price in paise. Cost is derived as 70%.
_PRICES = {
    "PANEL-550": 550_000,
    "INV-ONG": 2_500_000,
    "INV-OFG": 2_800_000,
    "BAT-1KWH": 1_800_000,
    "CC-MPPT": 450_000,
    "STAND": 80_000,
    "WIRE-BUNDLE": 120_000,
    "CONN-MC4": 25_000,
    "SW-DC": 15_000,
    "BOX-AC": 35_000,
    "EARTH": 20_000,
    "SVC-INSTALL": 500_000,
}


def _price(code: str, kw: int) -> int:
    if code in {"INV-ONG", "INV-OFG"}:
        return _PRICES[code] + (kw - 1) * 400_000
    return _PRICES[code]


def system_quantities(kw: int, grid: str) -> list[tuple[str, int, str]]:
    panels = kw * 2
    rows: list[tuple[str, int, str]] = [
        ("PANEL-550", panels, "material"),
        ("INV-ONG" if grid == "on_grid" else "INV-OFG", 1, "material"),
    ]
    if grid == "off_grid":
        rows.append(("BAT-1KWH", kw, "material"))
        rows.append(("CC-MPPT", 1, "material"))
    rows.extend(
        [
            ("STAND", panels, "material"),
            ("WIRE-BUNDLE", 2, "material"),
            ("CONN-MC4", panels, "material"),
            ("SW-DC", 1, "material"),
            ("BOX-AC", 1, "material"),
            ("EARTH", 1, "material"),
            ("SVC-INSTALL", 1, "installation"),
        ]
    )
    return rows


def seed_package_templates(db: Session) -> None:
    if db.get(CatalogueComponent, "PANEL-550") is not None:
        return
    for code, name, unit in COMPONENTS:
        db.add(CatalogueComponent(code=code, name=name, unit=unit))
    db.flush()
    packages = list(db.scalars(select(SolarPackage)))
    by_code = {package.code: package for package in packages}
    for kw in range(1, 6):
        for grid, prefix in (("on_grid", "PKG-ONG"), ("off_grid", "PKG-OFG")):
            _add_version(
                db,
                by_code[f"{prefix}-{kw}"],
                system_quantities(kw, grid),
                kw,
                "Version 1 demonstration template.",
            )
    _add_version(
        db,
        by_code["PKG-PANEL-SET"],
        [
            ("PANEL-550", 10, "material"),
            ("STAND", 10, "material"),
            ("CONN-MC4", 10, "material"),
        ],
        1,
        "Version 1 panel set. No inverter and no wiring bundle.",
    )
    _add_version(
        db,
        by_code["SVC-INSTALL"],
        [("SVC-INSTALL", 1, "installation")],
        1,
        "Version 1 installation service only.",
    )


def _add_version(db: Session, package: SolarPackage, rows, kw: int, note: str) -> None:
    version = PackageTemplateVersion(
        package_id=package.id,
        version_number=1,
        is_current=True,
        note=note,
    )
    db.add(version)
    db.flush()
    for index, (code, quantity, kind) in enumerate(rows):
        price = _price(code, kw)
        db.add(
            PackageTemplateLine(
                version_id=version.id,
                component_code=code,
                line_kind=kind,
                quantity=quantity,
                unit_cost_minor=price * 70 // 100,
                unit_price_minor=price,
                sort_order=index,
            )
        )
