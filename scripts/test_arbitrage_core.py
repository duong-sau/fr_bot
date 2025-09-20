import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Server.PositionView.FrAbitrageCore import FrAbitrageCore
from Core.Define import Position, PositionSide, EXCHANGE

# Create a pair of positions for the same symbol
p_long = Position(symbol='BTC/USDT:USDT', side=PositionSide.LONG, amount=1.0, entry_price=25000, exchange=EXCHANGE.BITGET, margin=1)
p_short = Position(symbol='BTC/USDT:USDT', side=PositionSide.SHORT, amount=1.0, entry_price=25010, exchange=EXCHANGE.GATE, margin=1)

core = FrAbitrageCore()

# First refresh
core.check_position([p_long, p_short])
print('After first check:', len(core.positions))

# Second refresh with same data
core.check_position([p_long, p_short])
print('After second check:', len(core.positions))

