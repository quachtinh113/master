from __future__ import annotations

import pandas as pd

from bot.backtest import run_backtest, walk_forward
from bot.config import BotConfig


def main() -> None:
    # Placeholder loader: replace by your minute-level EURUSD feature pipeline.
    data = pd.DataFrame(
        columns=[
            "ts",
            "price",
            "spread_pips",
            "ema50_h1",
            "ema200_h1",
            "rsi14_h1",
            "rsi5_m15",
            "adx_h1",
            "atr_h1",
        ]
    )
    if data.empty:
        print("No data loaded. Provide minute bars + precomputed indicators to run backtest.")
        return

    result = run_backtest(data, BotConfig())
    print(f"Max DD: {result.max_drawdown:.2f} USD")
    print(f"Winrate: {result.winrate:.2%}")
    print(f"Profit factor: {result.profit_factor:.2f}")
    print("Session performance:")
    print(result.by_session)
    print("Hour-block performance:")
    print(result.by_hour_block)

    print("Walk-forward (3m train / 1m test, 3 folds):")
    for fold in walk_forward(data):
        print(fold)


if __name__ == "__main__":
    main()
