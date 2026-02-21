
import sys
import os

sys.path.append(os.getcwd())

from core.datasources.cache_manager import ParquetCacheManager
from dotenv import load_dotenv

def main():
    load_dotenv()
    manager = ParquetCacheManager()
    print("Starting full cache warmup...", flush=True)
    manager.convert_all()
    manager.merge_all()
    manager.generate_ohlcv()
    print("Full cache warmup complete!", flush=True)

if __name__ == "__main__":
    main()
