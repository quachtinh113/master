from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from bot.clock import SessionClock
from bot.config import BotConfig
from bot.dca import Basket, Layer, adverse_move_atr, basket_pnl_usd, should_add_layer
from bot.risk import RiskGuard
from bot.strategy import get_entry_signal


@dataclass
class MarketSnapshot:
    ts: datetime
    price: float
    spread_pips: float
    ema50_h1: float
    ema200_h1: float
    rsi14_h1: float
    rsi5_m15: float
    adx_h1: float
    atr_h1: float


@dataclass
class SessionClockExecutionBot:
    config: BotConfig = field(default_factory=BotConfig)

    def __post_init__(self) -> None:
        self.clock = SessionClock(self.config)
        self.risk = RiskGuard(self.config, start_equity=self.config.capital, day_peak_equity=self.config.capital)
        self.equity = self.config.capital
        self.basket: Basket | None = None
        self.trades_today = 0
        self.last_day = None
        self.used_blocks: set[str] = set()
        self._setup_logs()

    def _setup_logs(self) -> None:
        Path("logs").mkdir(exist_ok=True)
        logging.basicConfig(filename="logs/app.log", level=logging.INFO, format="%(asctime)s %(message)s")
        self.trade_file = Path("logs/trades.csv")
        if not self.trade_file.exists():
            with self.trade_file.open("w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["ts", "event", "side", "price", "layers", "pnl", "session", "block", "risk_state"])

    def _session_name(self, ts: datetime) -> str:
        local = ts.astimezone(self.clock.tz).timetz().replace(tzinfo=None)
        for s in self.config.sessions:
            if s.start <= local <= s.end:
                return s.name
        return "OFF"

    def _write_trade(self, snap: MarketSnapshot, event: str, pnl: float = 0.0, risk_state: str = "ok") -> None:
        block = self.clock.block_key(snap.ts)
        with self.trade_file.open("a", newline="") as f:
            w = csv.writer(f)
            w.writerow([
                snap.ts.isoformat(),
                event,
                self.basket.side if self.basket else "-",
                snap.price,
                len(self.basket.layers) if self.basket else 0,
                round(pnl, 2),
                self._session_name(snap.ts),
                block,
                risk_state,
            ])

    def on_minute(self, snap: MarketSnapshot) -> None:
        if self.last_day != snap.ts.date():
            self.last_day = snap.ts.date()
            self.trades_today = 0
            self.used_blocks.clear()
            self.risk.on_new_day(self.equity)

        self.risk.update_peak(self.equity)
        self._manage_basket(snap)

        if self.basket is not None:
            return

        if self.trades_today >= self.config.max_trades_per_day:
            return

        risk_state = self.risk.evaluate(snap.ts, self.equity)
        if not risk_state.can_trade:
            return

        if not self.clock.is_entry_minute(snap.ts):
            return

        block = self.clock.block_key(snap.ts)
        if block in self.used_blocks:
            return

        signal = get_entry_signal(
            snap.ema50_h1,
            snap.ema200_h1,
            snap.rsi14_h1,
            snap.rsi5_m15,
            snap.adx_h1,
            snap.spread_pips,
            self.config.adx_entry_threshold,
            self.config.adx_no_trade_threshold,
            self.config.spread_max_pips,
        )
        if signal.side:
            self.basket = Basket(signal.side, atr_h1=snap.atr_h1, opened_at=snap.ts)
            self.basket.layers.append(Layer(snap.price, self.config.fixed_lot_per_layer, snap.ts))
            self.trades_today += 1
            self.used_blocks.add(block)
            self._write_trade(snap, "OPEN")
            logging.info("Open basket %s at %.5f", signal.side, snap.price)

    def _close_basket(self, snap: MarketSnapshot, reason: str) -> None:
        if not self.basket:
            return
        pnl = basket_pnl_usd(self.basket.side, self.basket.layers, snap.price)
        self.equity += pnl
        self.risk.register_realized(pnl)
        self._write_trade(snap, reason, pnl)
        logging.info("Close basket reason=%s pnl=%.2f", reason, pnl)
        self.basket = None

    def _manage_basket(self, snap: MarketSnapshot) -> None:
        if not self.basket:
            return

        adverse = adverse_move_atr(self.basket.side, self.basket.first_entry, snap.price, self.basket.atr_h1)
        if adverse > self.config.kill_switch_atr:
            self._close_basket(snap, "KILL_SWITCH")
            self.risk.cooldown_until = snap.ts + timedelta(hours=24)
            return

        pnl = basket_pnl_usd(self.basket.side, self.basket.layers, snap.price)
        age = self.basket.age_minutes(snap.ts)

        if 5 <= age <= 29 and pnl >= self.config.quick_profit_usd:
            self._close_basket(snap, "QUICK_PROFIT")
            return
        if 5 <= age <= 29 and pnl <= self.config.early_loss_usd:
            self._close_basket(snap, "EARLY_LOSS_CUT")
            return
        if age >= self.config.hard_time_stop_hours * 60 and pnl <= 0:
            self._close_basket(snap, "HARD_TIME_STOP")
            return

        if len(self.basket.layers) < self.config.max_layers and self.basket.total_lot < self.config.max_total_lot:
            if should_add_layer(
                self.basket.side,
                snap.price,
                self.basket.last_entry,
                self.basket.atr_h1,
                self.config.layer_step_atr,
            ):
                self.basket.layers.append(Layer(snap.price, self.config.fixed_lot_per_layer, snap.ts))
                self._write_trade(snap, "DCA_ADD")
