from datetime import datetime
from zoneinfo import ZoneInfo

from bot.clock import SessionClock
from bot.config import BotConfig


def test_entry_minute_and_session_filter():
    clock = SessionClock(BotConfig())
    vn = ZoneInfo("Asia/Ho_Chi_Minh")

    ok = datetime(2026, 1, 5, 8, 0, tzinfo=vn)
    bad_minute = datetime(2026, 1, 5, 8, 15, tzinfo=vn)
    off_session = datetime(2026, 1, 5, 12, 0, tzinfo=vn)

    assert clock.is_entry_minute(ok)
    assert not clock.is_entry_minute(bad_minute)
    assert not clock.is_entry_minute(off_session)
