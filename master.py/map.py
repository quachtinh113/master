import MetaTrader5 as mt5
import pandas as pd
import ta
import pytz
from datetime import datetime
import time

# 1. CẤU HÌNH HỆ THỐNG
SYMBOL = "EURUSD"
TIMEFRAMES = {
    '4h': mt5.TIMEFRAME_H4,
    '1h': mt5.TIMEFRAME_H1,
    '15m': mt5.TIMEFRAME_M15
}
RISK_PERCENT = 1  # 1% tài khoản mỗi lệnh

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
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df

# 4. TÍNH TOÁN CHỈ BÁO
def calculate_indicators(df):
    # EMA Trend (4H/1H)
    df['ema_fast'] = ta.trend.ema_indicator(df['close'], window=20)
    df['ema_slow'] = ta.trend.ema_indicator(df['close'], window=50)
    df['trend_up'] = df['ema_fast'] > df['ema_slow']
    df['trend_down'] = df['ema_fast'] < df['ema_slow']
    
    # WaveTrend LB (15M)
    hlc3 = (df['high'] + df['low'] + df['close']) / 3
    esa = ta.trend.ema_indicator(hlc3, window=10)
    d = ta.trend.ema_indicator(abs(hlc3 - esa), window=10)
    ci = (hlc3 - esa) / (0.015 * d)
    tci = ta.trend.ema_indicator(ci, window=21)
    wt1 = tci
    wt2 = wt1.rolling(window=4).mean()
    
    df['wt_cross_up'] = (wt1 > wt2) & (wt1.shift(1) <= wt2.shift(1)) & (wt1 < -60)
    df['wt_cross_down'] = (wt1 < wt2) & (wt1.shift(1) >= wt2.shift(1)) & (wt1 > 60)
    
    # EVEREX Flow (15M)
    flow = df['close'].diff() * df['volume']
    bull_flow = flow.clip(lower=0).rolling(window=5).mean()
    bear_flow = (-flow.clip(upper=0)).rolling(window=5).mean()
    flow_index = 2 * (100 - 100 / (1 + bull_flow / bear_flow)) - 100
    df['flow_up'] = flow_index > 0
    df['flow_down'] = flow_index < 0
    
    return df

# 5. QUẢN LÝ VỐN
def calculate_position_size():
    account_info = mt5.account_info()
    if account_info is None:
        print("Không lấy được thông tin tài khoản")
        return 0.1  # Lot mặc định
    
    balance = account_info.balance
    symbol_info = mt5.symbol_info(SYMBOL)
    price = symbol_info.ask if symbol_info else 1.0
    
    risk_amount = balance * RISK_PERCENT / 100
    lot_size = risk_amount / (price * 100000)  # Đối với EURUSD
    return round(lot_size, 2)

# 6. GỬI LỆNH
def place_order(side):
    symbol_info = mt5.symbol_info(SYMBOL)
    if symbol_info is None:
        print(f"Không tìm thấy thông tin {SYMBOL}")
        return None
    
    lot_size = calculate_position_size()
    point = symbol_info.point
    price = symbol_info.ask if side == 'buy' else symbol_info.bid
    deviation = 20
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": lot_size,
        "type": mt5.ORDER_BUY if side == 'buy' else mt5.ORDER_SELL,
        "price": price,
        "deviation": deviation,
        "magic": 2023,
        "comment": f"WT_LB+EVEREX {side}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    result = mt5.order_send(request)
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Lỗi đặt lệnh {side}:", result.comment)
    else:
        print(f"Đã đặt lệnh {side.upper()} | Giá: {price} | Lot: {lot_size}")
    
    return result

# 7. KIỂM TRA VỊ THẾ
def has_open_position():
    positions = mt5.positions_get(symbol=SYMBOL)
    return len(positions) > 0 if positions else False

# 8. LOGIC GIAO DỊCH
def trading_strategy():
    # Lấy dữ liệu đa khung thời gian
    df_4h = get_ohlcv(SYMBOL, TIMEFRAMES['4h'], 500)
    df_1h = get_ohlcv(SYMBOL, TIMEFRAMES['1h'], 500)
    df_15m = get_ohlcv(SYMBOL, TIMEFRAMES['15m'], 300)
    
    # Tính toán chỉ báo
    df_4h = calculate_indicators(df_4h)
    df_1h = calculate_indicators(df_1h)
    df_15m = calculate_indicators(df_15m)
    
    # Xu hướng chính (4H)
    trend_4h_up = df_4h['trend_up'].iloc[-1]
    trend_4h_down = df_4h['trend_down'].iloc[-1]
    
    # Xác nhận xu hướng (1H)
    trend_1h_up = df_1h['trend_up'].iloc[-1]
    trend_1h_down = df_1h['trend_down'].iloc[-1]
    
    # Tín hiệu vào lệnh (15M)
    last_15m = df_15m.iloc[-1]
    
    # Điều kiện giao dịch
    long_condition = (trend_4h_up and trend_1h_up and 
                     last_15m['wt_cross_up'] and last_15m['flow_up'])
    
    short_condition = (trend_4h_down and trend_1h_down and 
                       last_15m['wt_cross_down'] and last_15m['flow_down'])
    
    # Thực thi lệnh (chỉ giao dịch khi không có vị thế mở)
    if not has_open_position():
        if long_condition:
            place_order('buy')
        elif short_condition:
            place_order('sell')

# 9. VÒNG LẶP CHÍNH
def run_bot():
    print("=== HỆ THỐNG GIAO DỊCH ĐA KHUNG THỜI GIAN ===")
    print(f"Cặp: {SYMBOL} | Khung: 4H-1H-15M")
    print(f"Chiến lược: WT_LB + EVEREX + EMA Trend")
    
    while True:
        try:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n[{now}] Đang phân tích...")
            
            trading_strategy()
            
            # Chờ đến phút thứ 0, 15, 30, 45 mỗi giờ
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