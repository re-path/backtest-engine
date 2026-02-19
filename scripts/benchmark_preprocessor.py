import sys
import os
import time
import pandas as pd

# Add the project root to sys.path
sys.path.append(os.getcwd())

from core.datasources.sources import OHLCVSource
from dotenv import load_dotenv

def main():
    load_dotenv()
    
    symbol = "SCB"
    start_time = "2024-01-01"
    end_time = "2024-01-31"
    
    source = OHLCVSource()
    
    print(f"Benchmarking OHLCV query for {symbol} ({start_time} to {end_time})...")
    
    # Force CSV (by temporarily renaming the parquet file if it exists, or just calling with a dummy)
    # Actually, the preprocessor logic is: if parquet exists, use it.
    # To benchmark CSV, we can just look at the preprocessor logic.
    
    parquet_path = os.path.join("data", "processed", f"ticker={symbol}", "data.parquet")
    
    if os.path.exists(parquet_path):
        print("--- PARQUET (Optimized) ---")
        start = time.time()
        df_parquet = source.query(start_time, end_time, ticker=symbol)
        end = time.time()
        print(f"Time: {end - start:.4f}s")
        print(f"Rows: {len(df_parquet)}")
        
        # Test CSV by moving the parquet file temporarily
        temp_path = parquet_path + ".tmp"
        os.rename(parquet_path, temp_path)
        try:
            print("\n--- CSV (Baseline) ---")
            start = time.time()
            df_csv = source.query(start_time, end_time, ticker=symbol)
            end = time.time()
            print(f"Time: {end - start:.4f}s")
            print(f"Rows: {len(df_csv)}")
        finally:
            os.rename(temp_path, parquet_path)
    else:
        print("Parquet file not found. Warm up the cache first!")

if __name__ == "__main__":
    main()
