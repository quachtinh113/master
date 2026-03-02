from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from bot.config import BotConfig


@dataclass
class SessionClock:
    config: BotConfig
    tz: ZoneInfo = ZoneInfo("Asia/Ho_Chi_Minh")

    def _in_session(self, dt: datetime) -> bool:
        current = dt.timetz().replace(tzinfo=None)
        for session in self.config.sessions:
            if session.start <= current <= session.end:
                return True
        return False

    def is_entry_minute(self, dt: datetime) -> bool:
        local = dt.astimezone(self.tz)
        return local.minute in (0, 30) and self._in_session(local)

    def block_key(self, dt: datetime) -> str:
        local = dt.astimezone(self.tz)
        block_minute = 0 if local.minute < 30 else 30
        return local.strftime(f"%Y-%m-%d %H:{block_minute:02d}")
