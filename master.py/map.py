import time
from datetime import datetime

import MetaTrader5 as mt5
import pandas as pd
import ta

# 1. CẤU HÌNH HỆ THỐNG (QUANT)
SYMBOL = "EURUSD"
TIMEFRAMES = {
    "4h": mt5.TIMEFRAME_H4,
    "1h": mt5.TIMEFRAME_H1,
    "15m": mt5.TIMEFRAME_M15,
}

RISK_PERCENT = 1.0  # % rủi ro mỗi lệnh
MIN_SIGNAL_SCORE = 3  # ngưỡng điểm để vào lệnh
SL_ATR_MULTIPLIER = 1.5
TP_RR_RATIO = 2.0

# Tham số bộ lọc/điểm số
WT_OVERSOLD = -60
WT_OVERBOUGHT = 60
FLOW_WINDOW = 5
VOLATILITY_THRESHOLD = 0.0007  # ATR(14)/close tối thiểu
MAX_SL_PIPS = 40
MIN_LOT = 0.01


# 2. KHỞI TẠO KẾT NỐI MT5
def initialize_mt5():
    if not mt5.initialize():
        print("Khởi tạo MT5 thất bại, lỗi:", mt5.last_error())
        return False

    print("Kết nối MT5 thành công!")
    print("Phiên bản MT5:", mt5.version())
    return True


# 3. LẤY DỮ LIỆU GIÁ
def get_ohlcv(symbol, timeframe, n_candles):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n_candles)
    if rates is None or len(rates) == 0:
        return pd.DataFrame()

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df.set_index("time", inplace=True)
    return df


# 4. TÍNH TOÁN CHỈ BÁO
def calculate_indicators(df):
    if df.empty:
        return df

    # EMA trend
    df["ema_fast"] = ta.trend.ema_indicator(df["close"], window=20)
    df["ema_slow"] = ta.trend.ema_indicator(df["close"], window=50)
    df["trend_up"] = df["ema_fast"] > df["ema_slow"]
    df["trend_down"] = df["ema_fast"] < df["ema_slow"]

    # WaveTrend
    hlc3 = (df["high"] + df["low"] + df["close"]) / 3
    esa = ta.trend.ema_indicator(hlc3, window=10)
    d = ta.trend.ema_indicator(abs(hlc3 - esa), window=10)
    ci = (hlc3 - esa) / (0.015 * d.replace(0, pd.NA))
    tci = ta.trend.ema_indicator(ci, window=21)
    wt1 = tci
    wt2 = wt1.rolling(window=4).mean()

    df["wt_cross_up"] = (wt1 > wt2) & (wt1.shift(1) <= wt2.shift(1)) & (wt1 < WT_OVERSOLD)
    df["wt_cross_down"] = (wt1 < wt2) & (wt1.shift(1) >= wt2.shift(1)) & (wt1 > WT_OVERBOUGHT)

    # Everex flow
    flow = df["close"].diff() * df["volume"]
    bull_flow = flow.clip(lower=0).rolling(window=FLOW_WINDOW).mean()
    bear_flow = (-flow.clip(upper=0)).rolling(window=FLOW_WINDOW).mean().replace(0, pd.NA)
    flow_index = 2 * (100 - 100 / (1 + bull_flow / bear_flow)) - 100
    df["flow_up"] = flow_index > 0
    df["flow_down"] = flow_index < 0

    # Volatility filter
    df["atr"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)
    df["atr_ratio"] = df["atr"] / df["close"]
    df["volatility_ok"] = df["atr_ratio"] > VOLATILITY_THRESHOLD

    return df


# 5. QUẢN LÝ VỐN THEO STOP LOSS
def calculate_position_size(stop_loss_pips):
    account_info = mt5.account_info()
    symbol_info = mt5.symbol_info(SYMBOL)

    if account_info is None or symbol_info is None:
        print("Không lấy được thông tin tài khoản/symbol")
        return MIN_LOT

    stop_loss_pips = max(1.0, min(stop_loss_pips, MAX_SL_PIPS))
    risk_amount = account_info.balance * RISK_PERCENT / 100

    pip_value_per_lot = 10.0  # xấp xỉ cho EURUSD
    lot_size = risk_amount / (stop_loss_pips * pip_value_per_lot)

    lot_step = symbol_info.volume_step if symbol_info.volume_step else 0.01
    min_volume = symbol_info.volume_min if symbol_info.volume_min else MIN_LOT
    max_volume = symbol_info.volume_max if symbol_info.volume_max else 100.0

    lot_size = max(min_volume, min(max_volume, lot_size))
    lot_size = round(lot_size / lot_step) * lot_step

    return round(lot_size, 2)


# 6. GỬI LỆNH
def place_order(side, stop_loss_pips):
    symbol_info = mt5.symbol_info(SYMBOL)
    if symbol_info is None:
        print(f"Không tìm thấy thông tin {SYMBOL}")
        return None

    lot_size = calculate_position_size(stop_loss_pips)
    point = symbol_info.point
    pip_size = point * 10

    price = symbol_info.ask if side == "buy" else symbol_info.bid
    sl_distance = stop_loss_pips * pip_size
    tp_distance = sl_distance * TP_RR_RATIO

    sl = price - sl_distance if side == "buy" else price + sl_distance
    tp = price + tp_distance if side == "buy" else price - tp_distance

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": lot_size,
        "type": mt5.ORDER_BUY if side == "buy" else mt5.ORDER_SELL,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": 2023,
        "comment": f"QUANT_WT_FLOW_{side}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)

    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Lỗi đặt lệnh {side}:", result.comment if result else "order_send failed")
    else:
        print(
            f"Đã đặt lệnh {side.upper()} | Giá: {price:.5f} | Lot: {lot_size} | "
            f"SL: {sl:.5f} | TP: {tp:.5f}"
        )

    return result


# 7. KIỂM TRA VỊ THẾ
def has_open_position():
    positions = mt5.positions_get(symbol=SYMBOL)
    return len(positions) > 0 if positions else False


# 8. CHẤM ĐIỂM TÍN HIỆU QUANT
def score_signal(trend_4h_up, trend_1h_up, trend_4h_down, trend_1h_down, last_15m):
    long_score = 0
    short_score = 0

    if trend_4h_up:
        long_score += 1
    if trend_1h_up:
        long_score += 1
    if bool(last_15m["wt_cross_up"]):
        long_score += 1
    if bool(last_15m["flow_up"]):
        long_score += 1
    if bool(last_15m["volatility_ok"]):
        long_score += 1

    if trend_4h_down:
        short_score += 1
    if trend_1h_down:
        short_score += 1
    if bool(last_15m["wt_cross_down"]):
        short_score += 1
    if bool(last_15m["flow_down"]):
        short_score += 1
    if bool(last_15m["volatility_ok"]):
        short_score += 1

    return long_score, short_score


# 9. LOGIC GIAO DỊCH
def trading_strategy():
    df_4h = calculate_indicators(get_ohlcv(SYMBOL, TIMEFRAMES["4h"], 500))
    df_1h = calculate_indicators(get_ohlcv(SYMBOL, TIMEFRAMES["1h"], 500))
    df_15m = calculate_indicators(get_ohlcv(SYMBOL, TIMEFRAMES["15m"], 300))

    if df_4h.empty or df_1h.empty or df_15m.empty:
        print("Thiếu dữ liệu thị trường, bỏ qua vòng này")
        return

    trend_4h_up = bool(df_4h["trend_up"].iloc[-1])
    trend_4h_down = bool(df_4h["trend_down"].iloc[-1])
    trend_1h_up = bool(df_1h["trend_up"].iloc[-1])
    trend_1h_down = bool(df_1h["trend_down"].iloc[-1])
    last_15m = df_15m.iloc[-1]

    long_score, short_score = score_signal(
        trend_4h_up, trend_1h_up, trend_4h_down, trend_1h_down, last_15m
    )

    stop_loss_pips = max(5.0, min(MAX_SL_PIPS, (last_15m["atr"] / (mt5.symbol_info(SYMBOL).point * 10)) * SL_ATR_MULTIPLIER))

    print(
        f"Signal score | LONG: {long_score}/5 | SHORT: {short_score}/5 | "
        f"ATR ratio: {last_15m['atr_ratio']:.5f}"
    )

    if has_open_position():
        return

    if long_score >= MIN_SIGNAL_SCORE and long_score > short_score:
        place_order("buy", stop_loss_pips)
    elif short_score >= MIN_SIGNAL_SCORE and short_score > long_score:
        place_order("sell", stop_loss_pips)


# 10. VÒNG LẶP CHÍNH
def run_bot():
    print("=== HỆ THỐNG GIAO DỊCH QUANT ĐA KHUNG THỜI GIAN ===")
    print(f"Cặp: {SYMBOL} | Khung: 4H-1H-15M")
    print("Chiến lược: EMA Trend + WT + Flow + Volatility + Signal Scoring")

    while True:
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{now}] Đang phân tích...")

            trading_strategy()

            sleep_time = 60 * 15 - (time.time() % (60 * 15))
            time.sleep(sleep_time)
        except Exception as e:
            print(f"Lỗi: {e}")
            time.sleep(60)


if __name__ == "__main__":
    if initialize_mt5():
        try:
            run_bot()
        finally:
            mt5.shutdown()
