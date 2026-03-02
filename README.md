## Session Clock Execution Bot (EURUSD)

Python 3.10+ trading bot architecture for a 30,000 USD account with:
- Session-clock entry (VN time, minute 00/30)
- Trend + pullback entry filters (EMA/RSI/ADX + spread guard)
- Hybrid DCA with ATR spacing
- Basket exit priority and kill-switch cooldown
- Risk guard (daily/intraday/total DD + daily profit cap)
- Backtest and walk-forward stubs
- Logs: `logs/app.log`, `logs/trades.csv`

### Run tests

```bash
pytest -q
```

### Main entry

```bash
python master.py/map.py
```
