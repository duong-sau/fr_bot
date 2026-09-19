import unittest

from Core.FundingScanner import FundingRateScanner


class DummyPublicExchange:
    """Stub mimicking ccxt's public fetch_funding_rates() — no API key involved."""

    def __init__(self, response):
        self._response = response
        self.call_count = 0

    def fetch_funding_rates(self):
        self.call_count += 1
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


class TestFundingRateScanner(unittest.TestCase):
    def _make_scanner(self, clients):
        return FundingRateScanner(exchange_ids=list(clients.keys()), clients=clients)

    def test_scan_exchange_parses_and_filters_by_quote(self):
        clients = {
            "bitget": DummyPublicExchange({
                "BTC/USDT:USDT": {"fundingRate": "0.0001", "markPrice": "60000", "fundingTimestamp": 1700000000000},
                "BTC/USD:BTC": {"fundingRate": "0.0002"},  # not USDT-margined, should be skipped
            }),
        }
        scanner = self._make_scanner(clients)
        scanner._scan_exchange("bitget")

        status = scanner.get_status()
        self.assertEqual(status["symbol_count"]["bitget"], 1)
        self.assertIsNone(status["errors"]["bitget"])
        self.assertIsNotNone(status["last_scan"]["bitget"])

    def test_scan_exchange_records_error_without_raising(self):
        clients = {"gate": DummyPublicExchange(RuntimeError("network down"))}
        scanner = self._make_scanner(clients)

        scanner._scan_exchange("gate")

        status = scanner.get_status()
        self.assertIn("network down", status["errors"]["gate"])
        self.assertEqual(status["symbol_count"]["gate"], 0)

    def test_get_top_pairs_ranks_by_spread_and_picks_high_low_exchange(self):
        clients = {
            "bitget": DummyPublicExchange({
                "BTC/USDT:USDT": {"fundingRate": "0.0005"},
                "ETH/USDT:USDT": {"fundingRate": "0.0001"},
            }),
            "gate": DummyPublicExchange({
                "BTC/USDT:USDT": {"fundingRate": "-0.0002"},
                "ETH/USDT:USDT": {"fundingRate": "0.00015"},
            }),
            "binance": DummyPublicExchange({
                "SOL/USDT:USDT": {"fundingRate": "0.0003"},  # only on one exchange -> excluded
            }),
        }
        scanner = self._make_scanner(clients)
        for ex_id in clients:
            scanner._scan_exchange(ex_id)

        pairs = scanner.get_top_pairs(limit=10)

        self.assertEqual(len(pairs), 2)  # SOL excluded, only present on binance
        best = pairs[0]
        self.assertEqual(best["symbol"], "BTC/USDT:USDT")
        self.assertEqual(best["high_exchange"], "bitget")
        self.assertEqual(best["low_exchange"], "gate")
        self.assertAlmostEqual(best["spread"], 0.0007)
        self.assertAlmostEqual(best["spread_pct"], 0.07)

        second = pairs[1]
        self.assertEqual(second["symbol"], "ETH/USDT:USDT")
        self.assertEqual(second["high_exchange"], "gate")
        self.assertEqual(second["low_exchange"], "bitget")

    def test_get_top_pairs_respects_min_spread_and_limit(self):
        clients = {
            "bitget": DummyPublicExchange({
                "BTC/USDT:USDT": {"fundingRate": "0.0005"},
                "ETH/USDT:USDT": {"fundingRate": "0.0001"},
            }),
            "gate": DummyPublicExchange({
                "BTC/USDT:USDT": {"fundingRate": "-0.0002"},
                "ETH/USDT:USDT": {"fundingRate": "0.00015"},
            }),
        }
        scanner = self._make_scanner(clients)
        for ex_id in clients:
            scanner._scan_exchange(ex_id)

        pairs = scanner.get_top_pairs(limit=1, min_spread_pct=0.05)

        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["symbol"], "BTC/USDT:USDT")


if __name__ == "__main__":
    unittest.main()
