import os
import pandas as pd
from typing import Optional, List, Dict, Any
from .duckdb_manager import DuckDBManager

class SQLPreprocessor:
    """
    Intelligent SQL Preprocessor for Backtest Engine.
    Routes queries to optimized Parquet files if available, otherwise falls back to Hive-partitioned CSVs.
    """
    
    def __init__(self):
        self.manager = DuckDBManager.get_instance()
        self.processed_dir = os.path.join(os.getenv("DATA_DIR", "data"), "processed")
        os.makedirs(self.processed_dir, exist_ok=True)

    def get_source_sql(self, ticker: str, start_time: Any, end_time: Any, columns: Optional[List[str]] = None) -> str:
        """
        Resolves the best data source and returns a DuckDB SQL snippet for the FROM clause.
        """
        parquet_path = os.path.join(self.processed_dir, f"ticker={ticker}", "data.parquet")
        
        if os.path.exists(parquet_path):
            # Using optimized Parquet source
            return f"read_parquet('{parquet_path}')"
        
        # Fallback to CSV Hive partitions
        # This requires the BaseDuckDBSource logic for globs
        # For simplicity in this engine, we'll return a placeholder or handle it in the source classes
        return "FALLBACK_CSV"

    def get_optimized_query(self, ticker: str, start_time: Any, end_time: Any, 
                            table_type: str = 'floorsheet', 
                            interval: Optional[str] = None) -> Dict[str, Any]:
        """
        Generates a full optimized query dictionary.
        """
        source_sql = self.get_source_sql(ticker, start_time, end_time)
        
        if source_sql == "FALLBACK_CSV":
            return {"type": "fallback", "ticker": ticker, "start": start_time, "end": end_time}
            
        if table_type == 'ohlcv' and interval:
            query = f"""
                SELECT 
                    time_bucket(INTERVAL '{interval}', timestamp) as timestamp,
                    '{ticker}' as ticker,
                    FIRST(price) as open,
                    MAX(price) as high,
                    MIN(price) as low,
                    LAST(price) as close,
                    SUM(quantity) as volume
                FROM {source_sql}
                WHERE timestamp >= ? AND timestamp < ?
                GROUP BY timestamp
                ORDER BY timestamp ASC
            """
        else:
            # Floorsheet / raw trades
            query = f"""
                SELECT * FROM {source_sql}
                WHERE timestamp >= ? AND timestamp < ?
                ORDER BY timestamp ASC
            """
            
        return {
            "type": "optimized",
            "sql": query,
            "params": [pd.to_datetime(start_time), pd.to_datetime(end_time)]
        }
