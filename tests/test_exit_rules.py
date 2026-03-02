from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from bot.engine import MarketSnapshot, SessionClockExecutionBot


def test_quick_profit_exit():
    bot = SessionClockExecutionBot()
    vn = ZoneInfo("Asia/Ho_Chi_Minh")
    t0 = datetime(2026, 1, 5, 8, 0, tzinfo=vn)

    open_snap = MarketSnapshot(t0, 1.1, 0.8, 1.2, 1.1, 55, 25, 25, 0.001)
    bot.on_minute(open_snap)
    assert bot.basket is not None

    close_snap = MarketSnapshot(t0 + timedelta(minutes=10), 1.1008, 0.8, 1.2, 1.1, 55, 40, 25, 0.001)
    bot.on_minute(close_snap)
    assert bot.basket is None
    assert bot.equity > bot.config.capital
