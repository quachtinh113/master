import MetaTrader5 as mt5
import pandas as pd
import ta
import pytz
from datetime import datetime
import time

# 1. CẤU HÌNH HỆ THỐNG
SYMBOL = "BTCUSDm"
TIMEFRAMES = {
    '4h': mt5.TIMEFRAME_H4,
    '1h': mt5.TIMEFRAME_H1,
    '15m': mt5.TIMEFRAME_M15
}
RISK_PERCENT = 1  # 1% tài khoản mỗi lệnh

# 2. THÔNG TIN TÀI KHOẢN DEMO EXNESS
ACCOUNT_NUMBER = 204987040
SERVER = "Exness-MT5Trial7"
PASSWORD = "87u3D1$6"  # Thay bằng mật khẩu thực

# 3. KHỞI TẠO KẾT NỐI MT5
def initialize_mt5():
    if not mt5.initialize():
        print("Khởi tạo MT5 thất bại, lỗi:", mt5.last_error())
        return False
    
    authorized = mt5.login(ACCOUNT_NUMBER, password=PASSWORD, server=SERVER)
    if authorized:
        account_info = mt5.account_info()
        print(f"\n✅ Kết nối thành công tài khoản #{ACCOUNT_NUMBER}")
        print(f"💰 Balance: {account_info.balance:.2f} USD | Đòn bẩy: 1:{account_info.leverage}")
        return True
    else:
        print("❌ Đăng nhập thất bại, lỗi:", mt5.last_error())
        return False

# 4. LẤY DỮ LIỆU GIÁ
def get_ohlcv(symbol, timeframe, n_candles):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n_candles)
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df

# 5. TÍNH TOÁN CHỈ BÁO
def calculate_indicators(df):
    # EMA Trend
    df['ema_fast'] = ta.trend.ema_indicator(df['close'], window=20)
    df['ema_slow'] = ta.trend.ema_indicator(df['close'], window=50)
    df['trend_up'] = df['ema_fast'] > df['ema_slow']
    df['trend_down'] = df['ema_fast'] < df['ema_slow']
    
    # WaveTrend LB
    hlc3 = (df['high'] + df['low'] + df['close']) / 3
    esa = ta.trend.ema_indicator(hlc3, window=10)
    d = ta.trend.ema_indicator(abs(hlc3 - esa), window=10)
    ci = (hlc3 - esa) / (0.015 * d)
    tci = ta.trend.ema_indicator(ci, window=21)
    wt1 = tci
    wt2 = wt1.rolling(window=4).mean()
    
    df['wt_cross_up'] = (wt1 > wt2) & (wt1.shift(1) <= wt2.shift(1)) & (wt1 < -60)
    df['wt_cross_down'] = (wt1 < wt2) & (wt1.shift(1) >= wt2.shift(1)) & (wt1 > 60)
    
    # EVEREX Flow
    flow = df['close'].diff() * df['volume']
    bull_flow = flow.clip(lower=0).rolling(window=5).mean()
    bear_flow = (-flow.clip(upper=0)).rolling(window=5).mean()
    flow_index = 2 * (100 - 100 / (1 + bull_flow / bear_flow)) - 100
    df['flow_up'] = flow_index > 0
    df['flow_down'] = flow_index < 0
    
    return df

# 6. QUẢN LÝ VỐN
def calculate_position_size():
    account_info = mt5.account_info()
    if account_info is None:
        return 0.1  # Lot mặc định
    
    balance = account_info.balance
    symbol_info = mt5.symbol_info(SYMBOL)
    price = symbol_info.ask if symbol_info else 1.0
    
    risk_amount = balance * RISK_PERCENT / 100
    lot_size = risk_amount / (price * 100000)  # Đối với EURUSD
    return round(max(lot_size, 0.01), 2)  # Tối thiểu 0.01 lot

# 7. GỬI LỆNH
def place_order(side):
    if not mt5.terminal_info().trade_allowed:
        print("⚠️ Tài khoản không cho phép giao dịch!")
        return None
    
    symbol_info = mt5.symbol_info(SYMBOL)
    if symbol_info is None:
        print(f"❌ Không tìm thấy thông tin {SYMBOL}")
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
        "comment": f"WT+EVEREX {side}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    result = mt5.order_send(request)
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"❌ Lỗi đặt lệnh {side}:", result.comment)
    else:
        print(f"✅ Đã đặt lệnh {side.upper()} {SYMBOL}")
        print(f"   ▪️Giá: {price:.5f} | Lot: {lot_size:.2f}")
        print(f"   ▪️Balance: {mt5.account_info().balance:.2f} USD")
    
    return result

# 8. KIỂM TRA VỊ THẾ
def has_open_position():
    positions = mt5.positions_get(symbol=SYMBOL)
    return len(positions) > 0 if positions else False

# 9. LOGIC GIAO DỊCH CHÍNH
def trading_strategy():
    print("\n" + "="*50)
    print(f"🔄 Đang phân tích {SYMBOL} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
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
    
    # Thực thi lệnh
    if not has_open_position():
        if long_condition:
            print("\n🎯 TÍN HIỆU MUA:")
            print(f"   ▪️Xu hướng 4H: {'UPTREND' if trend_4h_up else 'DOWNTREND'}")
            print(f"   ▪️Xác nhận 1H: {'BULLISH' if trend_1h_up else 'BEARISH'}")
            print(f"   ▪️WT_LB: {last_15m['wt_cross_up']} | EVEREX: {last_15m['flow_up']}")
            place_order('buy')
            
        elif short_condition:
            print("\n🎯 TÍN HIỆU BÁN:")
            print(f"   ▪️Xu hướng 4H: {'UPTREND' if trend_4h_up else 'DOWNTREND'}")
            print(f"   ▪️Xác nhận 1H: {'BULLISH' if trend_1h_up else 'BEARISH'}")
            print(f"   ▪️WT_LB: {last_15m['wt_cross_down']} | EVEREX: {last_15m['flow_down']}")
            place_order('sell')
        else:
            print("🔍 Không tìm thấy tín hiệu giao dịch phù hợp")
    else:
        print("⏳ Đang có vị thế mở, chờ tín hiệu đóng lệnh")

# 10. VÒNG LẶP CHÍNH
def run_bot():
    print("="*50)
    print("🚀 HỆ THỐNG GIAO DỊCH TỰ ĐỘNG")
    print(f"📊 Cặp: {SYMBOL} | Khung: 4H-1H-15M")
    print(f"📈 Chiến lược: WT_LB + EVEREX + EMA Trend")
    print(f"💵 Tài khoản: #{ACCOUNT_NUMBER} | Server: {SERVER}")
    print("="*50)
    
    while True:
        try:
            trading_strategy()
            
            # Chờ đến phút thứ 0, 15, 30, 45 mỗi giờ
            sleep_time = 60 * 15 - (time.time() % (60 * 15))
            print(f"\n⏳ Chờ {int(sleep_time/60)} phút tới...")
            time.sleep(sleep_time)
            
        except Exception as e:
            print(f"❌ CÓ LỖI XẢY RA:", str(e))
            time.sleep(60)

# KHỞI CHẠY CHƯƠNG TRÌNH
if __name__ == "__main__":
    if initialize_mt5():
        try:
            run_bot()
        except KeyboardInterrupt:
            print("\n🛑 Dừng hệ thống...")
        finally:
            mt5.shutdown()
            print("✅ Đã đóng kết nối MT5")