from bot.dca import next_layer_price, should_add_layer


def test_dca_spacing_buy_side():
    price = next_layer_price("BUY", last_entry=1.1000, atr_h1=0.0020, step_atr=0.35)
    assert round(price, 5) == 1.0993
    assert should_add_layer("BUY", market_price=1.0992, last_entry=1.1000, atr_h1=0.0020, step_atr=0.35)


def test_dca_spacing_sell_side():
    price = next_layer_price("SELL", last_entry=1.1000, atr_h1=0.0020, step_atr=0.35)
    assert round(price, 5) == 1.1007
    assert should_add_layer("SELL", market_price=1.1008, last_entry=1.1000, atr_h1=0.0020, step_atr=0.35)
