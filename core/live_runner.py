import argparse
import time
import sys
import os
import signal
import redis
import json
import importlib.util
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.getcwd())

from core.context_live import ContextLive

def load_strategy_class(strategy_name):
    STRATEGIES_DIR = os.getenv("STRATEGIES_DIR", "resources/strategies")
    strategy_path = os.path.join(STRATEGIES_DIR, f"{strategy_name}.py")
    if not os.path.exists(strategy_path):
        raise FileNotFoundError(f"Strategy file not found: {strategy_path}")

    spec = importlib.util.spec_from_file_location("StrategyModule", strategy_path)
    if spec is None or spec.loader is None:
         raise ImportError(f"Could not load strategy spec from {strategy_path}")
         
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if hasattr(module, "Strategy"):
        return module.Strategy
    else:
        import inspect
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and obj.__module__ == module.__name__:
                return obj
    raise ImportError(f"No Strategy class found in {strategy_path}")

class LiveRunner:
    def __init__(self, strategy_name: str, redis_host=None, redis_port=None):
        self.strategy_name = strategy_name
        host = redis_host or os.getenv("REDIS_HOST", "0.0.0.0")
        port = int(redis_port or os.getenv("REDIS_PORT", 6380))
        self.redis = redis.Redis(host=host, port=port, decode_responses=True)
        self.running = True
        self.strategy_instance = None
        self.context = None
        signal.signal(signal.SIGINT, self.handle_exit)
        signal.signal(signal.SIGTERM, self.handle_exit)

    def handle_exit(self, signum, frame):
        print(f"Received signal {signum}. Stopping...")
        self.running = False

    def run(self):
        print(f"Starting strategy: {self.strategy_name}")
        self.redis.set(f"strategy:{self.strategy_name}:status", "running")
        try:
            StrategyCls = load_strategy_class(self.strategy_name)
            self.strategy_instance = StrategyCls() 
            initial_balance = float(os.getenv("INITIAL_BALANCE", 10000.0))
            slippage = float(os.getenv("DEFAULT_SLIPPAGE", 0.01))
            self.context = ContextLive(initial_balance=initial_balance, slippage=slippage)
            print(f"Strategy initialized. Entering main loop...")
            while self.running:
                status = self.redis.get(f"strategy:{self.strategy_name}:status")
                if status == "stopping":
                    print("Stop signal received via Redis value.")
                    self.running = False
                    break
                time.sleep(1)
        except Exception as e:
            print(f"Error in LiveRunner: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.cleanup()

    def cleanup(self):
        print("Cleaning up...")
        print("Strategy closed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a live strategy.")
    parser.add_argument("--strategy", required=True, help="Name of the strategy to run (filename without extension)")
    parser.add_argument("--redis-host", help="Redis host")
    parser.add_argument("--redis-port", type=int, help="Redis port")
    args = parser.parse_args()
    runner = LiveRunner(args.strategy, redis_host=args.redis_host, redis_port=args.redis_port)
    runner.run()
