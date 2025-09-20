from Core.Define import PositionSide


class AbitragePosition:

    def __init__(self, position_1, position_2):
        assert position_1.symbol == position_2.symbol
        if position_1.side == PositionSide.LONG:
            self.long_position = position_1
            self.short_position = position_2
        else:
            self.short_position = position_1
            self.long_position = position_2
        self.unreal_pnl = 0

    def amount_difference(self):
            return abs(self.long_position.amount - self.short_position.amount) / self.long_position.amount * 100

    def __repr__(self):
        return f"AbitragePosition(symbol={self.long_position.symbol}, difference={self.amount_difference()}%)"


class FrAbitrageCore:
    def __init__(self):
        self.positions = []

    def check_position(self, positions):
        from collections import defaultdict

        symbol_groups = defaultdict(list)
        for pos in positions:
            symbol_groups[pos.symbol].append(pos)

        for symbol, pos_list in symbol_groups.items():
            longs = [p for p in pos_list if p.side == PositionSide.LONG]
            shorts = [p for p in pos_list if p.side == PositionSide.SHORT]
            for long_pos, short_pos in zip(longs, shorts):
                self.positions.append(AbitragePosition(long_pos, short_pos))


    def __repr__(self):
        return f"FrAbitrageCore(positions={self.positions})"
