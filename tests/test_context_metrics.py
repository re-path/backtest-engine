# tests/test_context_metrics.py
import unittest
from datetime import datetime
from core.context import Context

class TestContextMetrics(unittest.TestCase):
    def setUp(self):
        self.event_log = []
        self.context = Context(initial_balance=10000, slippage=0.0, event_log=self.event_log)

    def test_set_metric_basic(self):
        ts = datetime.now()
        self.context.set_metric("AAPL", ts, "sma_20", 150.5)
        
        self.assertIn("AAPL", self.context.custom_metrics)
        self.assertIn("sma_20", self.context.custom_metrics["AAPL"])
        self.assertEqual(len(self.context.custom_metrics["AAPL"]["sma_20"]), 1)
        self.assertEqual(self.context.custom_metrics["AAPL"]["sma_20"][0]['value'], 150.5)
        self.assertEqual(self.context.custom_metrics["AAPL"]["sma_20"][0]['timestamp'], ts)

    def test_set_metric_multiple_tickers_and_names(self):
        ts = datetime.now()
        self.context.set_metric("AAPL", ts, "sma_20", 150.5)
        self.context.set_metric("AAPL", ts, "rsi", 65.0)
        self.context.set_metric("TSLA", ts, "sma_20", 200.0)
        
        self.assertEqual(len(self.context.custom_metrics), 2)
        self.assertEqual(len(self.context.custom_metrics["AAPL"]), 2)
        self.assertEqual(len(self.context.custom_metrics["TSLA"]), 1)

    def test_set_metric_edge_cases(self):
        ts = datetime.now()
        # Test None value
        self.context.set_metric("AAPL", ts, "none_metric", None)
        self.assertIsNone(self.context.custom_metrics["AAPL"]["none_metric"][0]['value'])
        
        # Test empty string name
        self.context.set_metric("AAPL", ts, "", 10)
        self.assertIn("", self.context.custom_metrics["AAPL"])

    def test_set_metric_multiple_timestamps(self):
        ts1 = datetime(2024, 1, 1, 10, 0)
        ts2 = datetime(2024, 1, 1, 10, 1)
        
        self.context.set_metric("AAPL", ts1, "v", 1)
        self.context.set_metric("AAPL", ts2, "v", 2)
        
        metrics = self.context.custom_metrics["AAPL"]["v"]
        self.assertEqual(len(metrics), 2)
        self.assertEqual(metrics[0]['value'], 1)
        self.assertEqual(metrics[1]['value'], 2)

if __name__ == '__main__':
    unittest.main()
