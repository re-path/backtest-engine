from .preprocessor import SQLPreprocessor
from .duckdb_manager import DuckDBManager
from .sources import OHLCVSource, FloorsheetSource
from .cache_manager import ParquetCacheManager
import dotenv
import polars as pl

dotenv.load_dotenv()
_preprocessor = SQLPreprocessor()

def query(sql_template: str, **kwargs):
    return pl.from_pandas(_preprocessor.execute_query(sql_template, **kwargs))

__all__ = ['query', 'SQLPreprocessor', 'DuckDBManager', 'OHLCVSource', 'FloorsheetSource', 'ParquetCacheManager']
