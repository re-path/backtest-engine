
import duckdb
import os

class DuckDBManager:
    _instance = None
    _con = None

    def __init__(self):
        datasource_folder = os.getenv("DATASOURCE_FOLDER")
        if not datasource_folder:
            raise ValueError("DATASOURCE_FOLDER not set in environment variables")
        self.datasource_folder = datasource_folder
        self._ensure_connection()
        self._setup_master_views()

    def _ensure_connection(self):
        if self._con is None:
            self._con = duckdb.connect(database=":memory:")
            self._con.execute("PRAGMA threads=8") 
            self._con.execute("PRAGMA memory_limit='8GB'")

    def _setup_master_views(self):
        self._con.execute("CREATE SCHEMA IF NOT EXISTS raw")
        self._con.execute("CREATE SCHEMA IF NOT EXISTS ohlcv")
        
        processed_dir = os.path.abspath(os.path.join(os.getenv("DATA_DIR", "data"), "processed"))
        parquet_pattern = os.path.join(processed_dir, "ticker=*/data.parquet")
        
        if any(os.path.exists(os.path.join(processed_dir, d)) for d in os.listdir(processed_dir) if d.startswith("ticker=")) if os.path.exists(processed_dir) else False:
            self._con.execute(f"CREATE OR REPLACE VIEW raw.floorsheet AS SELECT * FROM read_parquet('{parquet_pattern}', hive_partitioning=1)")
            
            self._con.execute("""
                CREATE OR REPLACE VIEW ohlcv.all_day AS 
                SELECT 
                    time_bucket(INTERVAL '1 day', timestamp) as timestamp,
                    ticker,
                    FIRST(price) as open,
                    MAX(price) as high,
                    MIN(price) as low,
                    LAST(price) as close,
                    SUM(quantity) as volume
                FROM raw.floorsheet
                GROUP BY timestamp, ticker
                ORDER BY timestamp ASC
            """)

    def get_base_path(self):
        if self.datasource_folder.rstrip('/').endswith('floorsheets'):
             return self.datasource_folder
        else:
             return os.path.join(self.datasource_folder, "floorsheets")

    def execute(self, query, params=None):
        if params is None:
            params = []
        return self._con.execute(query, params)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
