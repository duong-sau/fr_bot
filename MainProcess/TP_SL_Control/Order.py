from Core.Tool import try_this


def open_take_profit_gate(client, symbol, side, quantity, price):
    try:
        order = try_this(client.createOrder,
                         params={'symbol': symbol,
                                 'type': 'market',
                                 'side': 'buy' if side == 'LONG' else 'sell',
                                 'amount': quantity,
                                 'price': price,
                                 'params': {
                                     "takeProfitPrice": price,
                                     'reduceOnly': True,
                                 }
                                 },
                            log_func=print, retries=5, delay=2)
        return order['id']
    except Exception as e:
        print(e)
        return False

def open_stop_loss_gate(client, symbol, side, quantity, price):
    try:
        order = try_this(client.createOrder,
                            params={'symbol': symbol,
                                    'type': 'market',
                                    'side': 'buy' if side == 'LONG' else 'sell',
                                    'amount': quantity,
                                    'price': price,
                                    'params': {
                                        "stopLossPrice": price,
                                        'reduceOnly': True,
                                        'holdSide': 'BUY' if side == 'LONG' else 'SELL'
                                        }
                                    },
                            log_func=print, retries=5, delay=2)
        return order['id']
    except Exception as e:
        print(e)
        return False

def open_take_profit_bitget(client, symbol, side, quantity, price):
    try:
        order = try_this(client.createOrder,
                         params={'symbol': symbol,
                                 'type': 'market',
                                 'side': 'BUY' if side == 'LONG' else 'SELL',
                                 'amount': quantity,
                                 'price': price,
                                 'params': {
                                     "takeProfitPrice": price,
                                     'reduceOnly': True,
                                     'holdSide': 'BUY' if side == 'LONG' else 'SELL'
                                 }
                                 },
                            log_func=print, retries=5, delay=2)
        return order['id']
    except Exception as e:
        print(e)
        return False

def open_stop_loss_bitget(client, symbol, side, quantity, price):
    try:
        order = try_this(client.createOrder,
                            params={'symbol': symbol,
                                    'type': 'market',
                                    'side': 'BUY' if side == 'LONG' else 'SELL',
                                    'amount': quantity,
                                    'price': price,
                                    'params': {
                                        "stopLossPrice": price,
                                        'reduceOnly': True,
                                        'holdSide': 'BUY' if side == 'LONG' else 'SELL'
                                        }
                                    },
                            log_func=print, retries=5, delay=2)
        return order['id']
    except Exception as e:
        print(e)
        return False
