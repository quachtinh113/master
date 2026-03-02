from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Layer:
    entry_price: float
    lot: float
    opened_at: datetime


@dataclass
class Basket:
    side: str
    atr_h1: float
    opened_at: datetime
    layers: list[Layer] = field(default_factory=list)

    @property
    def first_entry(self) -> float:
        return self.layers[0].entry_price

    @property
    def last_entry(self) -> float:
        return self.layers[-1].entry_price

    @property
    def total_lot(self) -> float:
        return sum(x.lot for x in self.layers)

    def age_minutes(self, now: datetime) -> int:
        return int((now - self.opened_at).total_seconds() // 60)


def next_layer_price(side: str, last_entry: float, atr_h1: float, step_atr: float) -> float:
    delta = atr_h1 * step_atr
    return last_entry - delta if side == "BUY" else last_entry + delta


def should_add_layer(
    side: str,
    market_price: float,
    last_entry: float,
    atr_h1: float,
    step_atr: float,
) -> bool:
    trigger = next_layer_price(side, last_entry, atr_h1, step_atr)
    return market_price <= trigger if side == "BUY" else market_price >= trigger


def adverse_move_atr(side: str, first_entry: float, market_price: float, atr_h1: float) -> float:
    raw = (first_entry - market_price) if side == "BUY" else (market_price - first_entry)
    return raw / atr_h1 if atr_h1 > 0 else 0.0


def basket_pnl_usd(side: str, layers: list[Layer], market_price: float, pip_value_per_lot: float = 10.0) -> float:
    pnl = 0.0
    for layer in layers:
        pips = (market_price - layer.entry_price) * 10_000
        if side == "SELL":
            pips *= -1
        pnl += pips * pip_value_per_lot * layer.lot
    return pnl
