import sys
import os
import argparse

# Add the project root to sys.path
sys.path.append(os.getcwd())

from core.datasources.cache_manager import ParquetCacheManager
from dotenv import load_dotenv

def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Warm up SQL Preprocessor Cache (CSV -> Parquet)")
    parser.add_argument("--symbol", type=str, help="Specific symbol to warm up (default: all)")
    
    args = parser.parse_args()
    
    manager = ParquetCacheManager()
    
    if args.symbol:
        # Get globs for specific symbol
        from core.datasources.duckdb_manager import DuckDBManager
        db_manager = DuckDBManager.get_instance()
        base_path = db_manager.get_base_path()
        day_glob = os.path.join(base_path, f"symbol={args.symbol}", "year=*", "month=*", "day=*", "*.csv")
        manager.convert_symbol_to_parquet(args.symbol, [day_glob])
    else:
        print("Starting full cache warmup...", flush=True)
        manager.warmup_all()
        print("Full cache warmup complete!", flush=True)

if __name__ == "__main__":
    main()
