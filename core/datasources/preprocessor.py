
import os
import pandas as pd
from typing import Optional, List, Dict, Any, Union
from .duckdb_manager import DuckDBManager
from jinja2 import Template

class SQLPreprocessor:
    def __init__(self):
        self.manager = DuckDBManager.get_instance()

    def preprocess(self, sql_template: str, **kwargs) -> str:
        template = Template(sql_template)
        return template.render(**kwargs)

    def execute_query(self, sql_template: str, **kwargs) -> pd.DataFrame:
        optimized_sql = self.preprocess(sql_template, **kwargs)
        params = kwargs.get('_params', [])
        try:
            return self.manager.execute(optimized_sql, params).df()
        except Exception as e:
            raise e

    def get_source_sql(self, ticker: str, start_time: Any, end_time: Any, columns: Optional[List[str]] = None) -> str:
        return f"SELECT * FROM raw.floorsheet WHERE ticker = '{ticker}'"

    def get_optimized_query(self, ticker: str, start_time: Any, end_time: Any, 
                            table_type: str = 'floorsheet', 
                            interval: Optional[str] = None) -> Dict[str, Any]:
        if table_type == 'ohlcv' and interval:
            query = f"""
                SELECT 
                    time_bucket(INTERVAL '{interval}', timestamp) as timestamp,
                    ticker,
                    FIRST(price) as open,
                    MAX(price) as high,
                    MIN(price) as low,
                    LAST(price) as close,
                    SUM(quantity) as volume
                FROM raw.floorsheet
                WHERE ticker = ? AND timestamp >= ? AND timestamp < ?
                GROUP BY timestamp, ticker
                ORDER BY timestamp ASC
            """
        else:
            query = f"""
                SELECT * FROM raw.floorsheet
                WHERE ticker = ? AND timestamp >= ? AND timestamp < ?
                ORDER BY timestamp ASC
            """
            
        return {
            "type": "optimized",
            "sql": query,
            "params": [ticker, pd.to_datetime(start_time), pd.to_datetime(end_time)]
        }
