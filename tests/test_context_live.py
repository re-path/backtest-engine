import unittest
import subprocess
import time
import os
import signal
import json
import pandas as pd
from core.context_live import ContextLive

class TestContextLive(unittest.TestCase):
    redis_process = None

    @classmethod
    def setUpClass(cls):
        print("Starting Redis server for testing...")
        cmd = [
            "redis-server",
            "--port", "6380",
            "--save", "",
            "--appendonly", "no"
        ]
        cls.redis_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1) # Wait for startup

    @classmethod
    def tearDownClass(cls):
        print("Stopping Redis server...")
        if cls.redis_process:
            cls.redis_process.terminate()
            cls.redis_process.wait()

    def setUp(self):
        # Clear redis data before each test
        self.context = ContextLive(initial_balance=10000.0, slippage=0.0)
        self.context.redis_client.flushall()
        # Re-init balance after flush
        self.context.set_balance(10000.0)

    def test_initial_balance(self):
        self.assertEqual(self.context.get_balance(), 10000.0)

    def test_buy_and_position(self):
        current_time = pd.Timestamp("2023-01-01 10:00:00")
        msg = self.context.buy("AAPL", 1000.0, 100.0, current_time)
        # With 0 delay, it executes immediately
        
        # Check balance: 1000 spent -> 9000 left
        self.assertEqual(self.context.get_balance(), 9000.0)
        
        # Check position
        pos = self.context.get_position("AAPL")
        self.assertIsNotNone(pos)
        self.assertEqual(pos.ticker, "AAPL")
        self.assertEqual(pos.share_units, 10.0) # 1000 / 100
        
        # Check Redis directly
        val = self.context.redis_client.hget("live:positions", "AAPL")
        self.assertIsNotNone(val)
        data = json.loads(val)
        self.assertEqual(data['ticker'], "AAPL")

    def test_sell(self):
        current_time = pd.Timestamp("2023-01-01 10:00:00")
        self.context.buy("AAPL", 1000.0, 100.0, current_time)
        
        # Sell half
        self.context.sell("AAPL", 5.0, 110.0, current_time)
        
        # Balance: 9000 + (5 * 110) = 9000 + 550 = 9550
        self.assertEqual(self.context.get_balance(), 9550.0)
        
        # Position: 5 shares left
        pos = self.context.get_position("AAPL")
        self.assertEqual(pos.share_units, 5.0)

    def test_state(self):
        self.context.set_state("foo", {"bar": 123})
        val = self.context.get_state("foo")
        self.assertEqual(val, {"bar": 123})
        
        # Check redis
        raw = self.context.redis_client.hget("live:state", "foo")
        self.assertEqual(json.loads(raw), {"bar": 123})

    def test_pending_orders(self):
        # Set delay
        self.context.execution_delay = 5
        current_time = pd.Timestamp("2023-01-01 10:00:00")
        
        self.context.buy("GOOG", 1000.0, 100.0, current_time)
        
        # Should be pending
        self.assertEqual(self.context.get_balance(), 10000.0)
        orders = self.context._get_pending_orders()
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0]['ticker'], "GOOG")
        
        # Process before delay
        self.context.process_pending_orders("GOOG", 100.0, current_time + pd.Timedelta(seconds=2))
        self.assertEqual(self.context.get_balance(), 10000.0)
        
        # Process after delay
        self.context.process_pending_orders("GOOG", 100.0, current_time + pd.Timedelta(seconds=6))
        self.assertEqual(self.context.get_balance(), 9000.0)
        orders = self.context._get_pending_orders()
        self.assertEqual(len(orders), 0)

if __name__ == '__main__':
    unittest.main()
