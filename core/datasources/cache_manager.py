import os
import pandas as pd
import duckdb
from typing import List, Any
from .duckdb_manager import DuckDBManager

class ParquetCacheManager:
    def __init__(self):
        self.manager = DuckDBManager.get_instance()
        self.processed_dir = os.path.join(os.getenv("DATA_DIR", "data"), "processed")
        os.makedirs(self.processed_dir, exist_ok=True)

    def convert_symbol_to_parquet(self, symbol: str, csv_globs: List[str]):
        if not csv_globs:
            return

        target_file = os.path.join(self.processed_dir, f"ticker={symbol}", "data.parquet")
        os.makedirs(os.path.dirname(target_file), exist_ok=True)

        print(f"Converting {symbol} to Parquet: {target_file}", flush=True)
        
        con = duckdb.connect(database=":memory:")
        mem_limit = "4GB"
        print(f"Setting DuckDB memory limit to {mem_limit}...", flush=True)
        con.execute(f"PRAGMA memory_limit='{mem_limit}'")
        con.execute("PRAGMA temp_directory='/tmp/duckdb_temp'")
        
        try:
            query = f"""
                COPY (
                    SELECT 
                        trade_time as timestamp,
                        symbol as ticker,
                        rate as price,
                        quantity,
                        * EXCLUDE (trade_time, symbol, rate, quantity)
                    FROM read_csv(?, 
                                  hive_partitioning=1, 
                                  union_by_name=1, 
                                  header=1, 
                                  auto_detect=1)
                    WHERE symbol = ?
                    ORDER BY trade_time ASC
                ) TO '{target_file}' (FORMAT 'PARQUET', COMPRESSION 'ZSTD')
            """
            con.execute(query, [csv_globs, symbol])
            print(f"Successfully created {target_file}", flush=True)
        except Exception as e:
            print(f"Error converting {symbol}: {e}", flush=True)
        finally:
            con.close()

    def warmup_all(self):
        base_path = self.manager.get_base_path()
        symbols = []
        for d in os.listdir(base_path):
            if d.startswith("symbol="):
                symbols.append(d.split("=")[1])
        
        for symbol in symbols:
            day_glob = os.path.join(base_path, f"symbol={symbol}", "year=*", "month=*", "day=*", "*.csv")
            self.convert_symbol_to_parquet(symbol, [day_glob])
