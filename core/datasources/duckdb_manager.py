
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

    def _ensure_connection(self):
        if self._con is None:
            self._con = duckdb.connect(database=":memory:")
            # Configure for high-throughput parallel CSV reading
            self._con.execute("PRAGMA threads=8") 
            self._con.execute("PRAGMA memory_limit='8GB'")

    def get_base_path(self):
        # Robust path construction: Handle if DATASOURCE_FOLDER already ends in 'floorsheets'
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
