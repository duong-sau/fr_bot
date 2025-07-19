from Exchange.Exchange import bitget_pro
import asyncio

async def main():
    long_exchange = bitget_pro
    symbol = "BTC/USDT:USDT"
    await long_exchange.create_order_ws(symbol=symbol, type='market', side="SELL", amount=0.01)

if __name__ == '__main__':
    asyncio.run(main())