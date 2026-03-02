from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SignalState:
    side: str | None
    reason: str


def get_entry_signal(
    ema50_h1: float,
    ema200_h1: float,
    rsi14_h1: float,
    rsi5_m15: float,
    adx_h1: float,
    spread_pips: float,
    adx_entry_threshold: float,
    adx_no_trade_threshold: float,
    spread_max_pips: float,
) -> SignalState:
    if spread_pips > spread_max_pips:
        return SignalState(None, "spread_guard")

    if adx_h1 < adx_no_trade_threshold:
        return SignalState(None, "adx_below_no_trade")

    trend_buy = ema50_h1 > ema200_h1
    trend_sell = ema50_h1 < ema200_h1

    if adx_h1 <= adx_entry_threshold:
        return SignalState(None, "adx_not_strong")

    if trend_buy and rsi14_h1 >= 50 and rsi5_m15 <= 30:
        return SignalState("BUY", "trend_pullback_buy")
    if trend_sell and rsi14_h1 <= 50 and rsi5_m15 >= 70:
        return SignalState("SELL", "trend_pullback_sell")

    return SignalState(None, "no_setup")
