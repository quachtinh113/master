# NowTrading 30M Basket EA (MT5 / MQL5)

Production-oriented single-symbol basket EA for **EURUSD** with 30-minute entry windows, multi-timeframe RSI/ADX signal gating, DCA scaling, risk guardrails, and structured logging.

## Strategy Rules

### Time engine
- Entry evaluation happens **only at local terminal minute 01 or 31**.
- One basket per 30-minute block is enforced.
- Optional session filter (`EnableLondonNYOnly`): only evaluates entries within local `StartHour`..`EndHour`.
- `DailyMaxBaskets` resets automatically on local day rollover.

### Signal gate (all conditions must pass)
**BUY**
1. RSI(14) H4 > 55
2. RSI(14) H1 > 50
3. RSI(14) M15 crosses **above 50** on the last closed M15 candle (`shift 2 -> shift 1`)
4. ADX(14) H1 > 22
5. Spread <= `MaxSpreadPoints`

**SELL**
1. RSI(14) H4 < 45
2. RSI(14) H1 < 50
3. RSI(14) M15 crosses **below 50** on the last closed M15 candle (`shift 2 -> shift 1`)
4. ADX(14) H1 > 22
5. Spread <= `MaxSpreadPoints`

### Basket structure
- Base lots split into **2 market orders** (`BaseLotsTotal/2` each).
- Optional limit order (`PendingLots`) offset by `PendingOffsetPips`:
  - BUY: below current ask
  - SELL: above current bid
- Basket identity is encoded in comment: `NTB|<basket_id>|BUY|SELL` and shared by all basket orders.

### DCA engine
- Adds a new market order only when price moves against the basket from the **last filled position price** by `SpacingPips`.
- Volume = `DcaLots`, capped by `MaxDcaLevels`.
- Stops adding DCA when floating DD > 6%, free margin % < configured threshold, or risk guard blocks.

### Basket TP
- `TpMode=0 (MONEY)`: close basket when basket floating profit >= `TargetProfitUSD`.
- `TpMode=1 (ATR)`: close basket when current price reaches weighted-average-entry ± `AtrMultiplierTP * ATR(14,M15)`.
  - BUY uses bid >= target.
  - SELL uses ask <= target.
- On TP: closes all market positions and deletes basket pending orders.

### Emergency exit
If basket age >= `EmergencyHours` (default 12h):
- BUY basket exits when RSI H4 < 45 and RSI D1 < 50.
- SELL basket exits when RSI H4 > 55 and RSI D1 > 50.

### Risk guard (new entries)
Blocks new basket creation when any are true:
- `DailyDrawdownPercent > 8` (input-driven)
- `TotalFloatingDrawdownPercent > 10` (input-driven)
- `ConsecutiveLosingBaskets >= 3`
- `NewsBlackout` inside ±15 minutes (manual-news-time stub included)

Also includes a clean `CorrelationGuard` stub for future multi-symbol expansion.

## Inputs
Key parameters:
- Execution: `InpMagic`, `DeviationPoints`, `SafetySLPips`
- Entry sizing: `BaseLotsTotal`, `UsePendingLimit`, `PendingLots`, `PendingOffsetPips`
- DCA: `DcaLots`, `SpacingPips`, `MaxDcaLevels`
- TP: `TpMode`, `TargetProfitUSD`, `AtrMultiplierTP`
- Filters: `MaxSpreadPoints`, `EnableLondonNYOnly`, `StartHour`, `EndHour`
- Risk: `MaxDailyDdPercent`, `MaxFloatingDdPercent`, `MinFreeMarginPercent`, `MaxConsecutiveLosingBaskets`
- News stub: `EnableNewsBlackout`, `ManualHighImpactNewsTime`, `NewsWindowMinutes`
- Logging: `LogLevel` (0 error, 1 info, 2 debug)

## Installation
1. Copy files into MT5 data folder:
   - `MQL5/Experts/NowTrading_30M_BasketEA.mq5`
   - `MQL5/Include/NowTrading/*.mqh`
2. Open MetaEditor and compile `NowTrading_30M_BasketEA.mq5`.
3. Attach EA to EURUSD chart.
4. Enable Algo Trading and configure inputs.

## Basket IDs
- Every new basket gets a unique integer ID based on local timestamp.
- All trades in the basket use the same comment prefix (`NTB|id|direction`) and same magic number.
- Basket manager scans positions/orders by symbol + magic + parsed comment to group lifecycle actions.

## Logging
### Journal
Structured `PrintFormat` logs for:
- signal gate evaluations
- risk guard decisions
- basket open/close
- DCA attempts
- emergency exits

### CSV
File path: `MQL5/Files/NowTrading/<symbol>_basket_log.csv`.

Columns:
`timestamp, symbol, basket_id, event_type, direction, lots, price, rsi_h4, rsi_h1, rsi_m15, adx_h1, atr_m15, spread, equity, free_margin, dd_daily, dd_floating, note`

## Parameter presets (small account ~1k)
- `BaseLotsTotal=0.20`
- `PendingLots=0.10`
- `DcaLots=0.20`
- `SpacingPips=30`
- `MaxDcaLevels=3`
- `TpMode=0`
- `TargetProfitUSD=20`
- `MaxSpreadPoints=25`
- `MaxDailyDdPercent=8`
- `MaxFloatingDdPercent=10`
- `MinFreeMarginPercent=50`

## Strategy Tester validation checklist
- Verify entries only print around minute **01/31**.
- Confirm RSI M15 cross uses closed bars (logs show prev2/prev1).
- Confirm basket TP closes positions and removes pending orders.
- Confirm DCA triggers from **last filled** order spacing, not average.
- Confirm emergency exit only after 12h gate and RSI H4/D1 alignment.
- Confirm risk guard logs blocked reasons (`daily_dd`, `float_dd`, `news_blackout`, etc.).
