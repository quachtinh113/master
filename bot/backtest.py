from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from bot.config import BotConfig
from bot.engine import MarketSnapshot, SessionClockExecutionBot


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    max_drawdown: float
    winrate: float
    profit_factor: float
    avg_basket_duration_min: float
    avg_layers_used: float
    by_session: pd.DataFrame
    by_hour_block: pd.DataFrame


def run_backtest(data: pd.DataFrame, config: BotConfig | None = None) -> BacktestResult:
    bot = SessionClockExecutionBot(config or BotConfig())
    closed = []
    equity_points = []

    for _, row in data.iterrows():
        snap = MarketSnapshot(
            ts=row["ts"],
            price=row["price"],
            spread_pips=row["spread_pips"],
            ema50_h1=row["ema50_h1"],
            ema200_h1=row["ema200_h1"],
            rsi14_h1=row["rsi14_h1"],
            rsi5_m15=row["rsi5_m15"],
            adx_h1=row["adx_h1"],
            atr_h1=row["atr_h1"],
        )
        before = bot.equity
        bot.on_minute(snap)
        if bot.equity != before:
            closed.append({"ts": snap.ts, "pnl": bot.equity - before})
        equity_points.append((snap.ts, bot.equity))

    curve = pd.Series({k: v for k, v in equity_points}).sort_index()
    roll_max = curve.cummax()
    dd = (roll_max - curve).max()

    closed_df = pd.DataFrame(closed)
    wins = closed_df[closed_df.pnl > 0]
    losses = closed_df[closed_df.pnl < 0]
    winrate = len(wins) / len(closed_df) if len(closed_df) else 0.0
    profit_factor = wins.pnl.sum() / abs(losses.pnl.sum()) if len(losses) else float("inf")

    trades = pd.read_csv("logs/trades.csv") if pd.io.common.file_exists("logs/trades.csv") else pd.DataFrame()
    baskets = trades[trades.event.isin(["QUICK_PROFIT", "EARLY_LOSS_CUT", "HARD_TIME_STOP", "KILL_SWITCH"])].copy() if not trades.empty else pd.DataFrame()
    avg_layers = baskets.layers.mean() if not baskets.empty else 0.0
    by_session = baskets.groupby("session")["pnl"].agg(["count", "sum", "mean"]) if not baskets.empty else pd.DataFrame()
    by_hour = baskets.groupby("block")["pnl"].agg(["count", "sum", "mean"]) if not baskets.empty else pd.DataFrame()

    return BacktestResult(
        equity_curve=curve,
        max_drawdown=float(dd),
        winrate=float(winrate),
        profit_factor=float(profit_factor),
        avg_basket_duration_min=0.0,
        avg_layers_used=float(avg_layers),
        by_session=by_session,
        by_hour_block=by_hour,
    )


def walk_forward(data: pd.DataFrame) -> list[dict]:
    folds = []
    for i in range(3):
        train = data.iloc[i * 30 * 24 * 60:(i + 3) * 30 * 24 * 60]
        test = data.iloc[(i + 3) * 30 * 24 * 60:(i + 4) * 30 * 24 * 60]
        best = {"layer_step_atr": 0.35, "adx_threshold": 20}
        folds.append({"fold": i + 1, "train_rows": len(train), "test_rows": len(test), "best": best})
    return folds
