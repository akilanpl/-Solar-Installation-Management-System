"""Planned provider boundaries.

These types describe how later phases will call weather, payments, and
complaint summarisation. No adapter in Phase 1 returns successful weather,
payment, or AI data. `registered_providers` stays empty so a caller cannot
accidentally treat a stub as a live integration.
"""

from typing import Literal, Protocol


class WeatherReading(Protocol):
    kind: Literal["observation", "forecast"]
    source: str


class WeatherProvider(Protocol):
    def fetch(
        self, latitude: float, longitude: float, kind: Literal["observation", "forecast"]
    ): ...


class PaymentProvider(Protocol):
    def create_intent(self, amount_minor: int, currency_code: str, reference: str): ...


class ComplaintSummarizer(Protocol):
    def suggest(self, complaint_text: str): ...


def registered_providers() -> dict[str, object]:
    return {}
