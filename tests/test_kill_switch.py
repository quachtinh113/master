from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from bot.engine import MarketSnapshot, SessionClockExecutionBot


def test_kill_switch_sets_cooldown_and_closes():
    bot = SessionClockExecutionBot()
    vn = ZoneInfo("Asia/Ho_Chi_Minh")
    t0 = datetime(2026, 1, 5, 8, 0, tzinfo=vn)

    bot.on_minute(MarketSnapshot(t0, 1.1000, 0.8, 1.2, 1.1, 55, 25, 25, 0.001))
    assert bot.basket is not None

    # adverse > 3 ATR for BUY => drop > 0.0030
    t1 = t0 + timedelta(minutes=1)
    bot.on_minute(MarketSnapshot(t1, 1.0965, 0.8, 1.2, 1.1, 55, 20, 25, 0.001))
    assert bot.basket is None
    assert bot.risk.cooldown_until is not None
    assert bot.risk.cooldown_until > t1
