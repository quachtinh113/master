from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from bot.config import BotConfig


@dataclass
class RiskState:
    can_trade: bool
    reason: str


@dataclass
class RiskGuard:
    config: BotConfig
    start_equity: float
    daily_realized_pnl: float = 0.0
    day_peak_equity: float = 0.0
    cooldown_until: datetime | None = None

    def on_new_day(self, current_equity: float) -> None:
        self.daily_realized_pnl = 0.0
        self.day_peak_equity = current_equity

    def register_realized(self, pnl: float) -> None:
        self.daily_realized_pnl += pnl

    def update_peak(self, current_equity: float) -> None:
        self.day_peak_equity = max(self.day_peak_equity, current_equity)

    def evaluate(self, now: datetime, current_equity: float) -> RiskState:
        if self.cooldown_until and now < self.cooldown_until:
            return RiskState(False, "kill_switch_cooldown")

        total_dd = self.start_equity - current_equity
        if total_dd >= self.config.total_dd_limit_usd:
            return RiskState(False, "total_dd_limit")

        if self.daily_realized_pnl <= -self.config.daily_dd_limit_usd:
            return RiskState(False, "daily_dd_limit")

        if self.daily_realized_pnl >= self.config.daily_profit_cap_usd:
            return RiskState(False, "daily_profit_cap")

        intraday_dd = self.day_peak_equity - current_equity
        if intraday_dd >= self.config.intraday_peak_dd_limit_usd:
            return RiskState(False, "intraday_peak_dd")

        return RiskState(True, "ok")
