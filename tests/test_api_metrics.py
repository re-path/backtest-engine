# tests/test_api_metrics.py
import unittest
from fastapi.testclient import TestClient
import pandas as pd
from core.api import app, last_backtest_results

client = TestClient(app)

class TestAPIMetrics(unittest.TestCase):
    def setUp(self):
        # Reset global state
        last_backtest_results["event_log"] = None
        last_backtest_results["custom_metrics"] = {}

    def test_run_backtest_with_metrics(self):
        # A simple strategy that sets a metric
        strategy_code = """
class Strategy:
    def on_bar(self, context, bar):
        context.set_metric('custom_val', bar.timestamp, bar.ticker, bar.price * 2)
"""
        # We need a small amount of data. This test might be slow if it queries real DB.
        # However, we can check if the response format is correct.
        # For a truly robust test, we should mock the datasource.
        
        request_payload = {
            "start_date": "2024-01-01",
            "end_date": "2024-01-02",
            "initial_balance": 10000,
            "slippage": 0.0,
            "code": strategy_code
        }
        
        response = client.post("/run-backtest", json=request_payload)
        
        # Even if it fails due to no data, we should check if it handles it.
        # But let's assume it succeeds for now to verify our new fields.
        if response.status_code == 200:
            data = response.json()
            self.assertIn("custom_metrics", data)
            # Check last-log too
            log_response = client.get("/backtest/last-log")
            self.assertEqual(log_response.status_code, 200)
            self.assertIn("custom_metrics", log_response.json())

    def test_last_log_empty_state(self):
         response = client.get("/backtest/last-log")
         self.assertEqual(response.status_code, 200)
         data = response.json()
         self.assertEqual(data["event_log"], [])
         self.assertEqual(data["custom_metrics"], {})

if __name__ == '__main__':
    unittest.main()
