import os
import polars as pl
import dotenv
from .preprocessor import SQLPreprocessor

dotenv.load_dotenv()
_preprocessor = SQLPreprocessor()

def query(sql_template: str, **kwargs):
    data_dir = os.getenv("DATA_DIR", "data")
    ohlcv_db = os.path.join(data_dir, "ohlcv.duckdb")
    raw_db = os.path.join(data_dir, "raw.duckdb")

    sql_prefix = f""" 
    ATTACH '{ohlcv_db}' AS ohlcv; 
    ATTACH '{raw_db}' AS raw; 
    CREATE OR REPLACE TEMPORARY VIEW floorsheet AS 
    SELECT 
        symbol AS ticker,
        trade_time AS timestamp,
        rate AS price,
        * EXCLUDE (symbol, trade_time, rate)
    FROM raw.floorsheet;
    """
    
    _preprocessor.execute_query(sql_prefix)
    try:
        df = pl.from_pandas(_preprocessor.execute_query(sql_template, **kwargs))
    except Exception as e:
        print(f"Error executing query: {e}")
        df = pl.DataFrame()
    
    _preprocessor.execute_query(""" 
    DETACH ohlcv;
    DETACH raw;
    """)
    return df
