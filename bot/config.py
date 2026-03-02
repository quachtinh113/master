from dataclasses import dataclass, field
from datetime import time


@dataclass(frozen=True)
class SessionWindow:
    name: str
    start: time
    end: time


@dataclass(frozen=True)
class BotConfig:
    symbol: str = "EURUSD"
    capital: float = 30_000.0
    spread_max_pips: float = 2.0
    max_trades_per_day: int = 6
    max_layers: int = 10
    fixed_lot_per_layer: float = 0.30
    max_total_lot: float = 3.0
    layer_step_atr: float = 0.35
    kill_switch_atr: float = 3.0
    quick_profit_usd: float = 20.0
    early_loss_usd: float = -20.0
    hard_time_stop_hours: int = 12
    daily_dd_limit_usd: float = 600.0
    intraday_peak_dd_limit_usd: float = 450.0
    total_dd_limit_usd: float = 2400.0
    daily_profit_cap_usd: float = 300.0
    adx_entry_threshold: float = 20.0
    adx_no_trade_threshold: float = 18.0
    sessions: list[SessionWindow] = field(
        default_factory=lambda: [
            SessionWindow("ASIA", time(8, 0), time(11, 30)),
            SessionWindow("EUROPE", time(13, 0), time(16, 30)),
            SessionWindow("US", time(19, 0), time(22, 30)),
        ]
    )
