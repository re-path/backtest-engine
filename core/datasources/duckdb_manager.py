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
            self._con.execute("PRAGMA threads=8") 
            self._con.execute("PRAGMA memory_limit='4GB'")

    def get_base_path(self):
        return self.datasource_folder

    def execute(self, query, params=None):
        if params is None:
            params = []
        return self._con.execute(query, params)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
