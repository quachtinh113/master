from datetime import datetime

from bot.config import BotConfig
from bot.risk import RiskGuard


def test_daily_dd_blocks_trading():
    cfg = BotConfig()
    risk = RiskGuard(cfg, start_equity=cfg.capital, day_peak_equity=cfg.capital)
    risk.register_realized(-650)
    state = risk.evaluate(datetime.utcnow(), cfg.capital - 650)
    assert not state.can_trade
    assert state.reason == "daily_dd_limit"
