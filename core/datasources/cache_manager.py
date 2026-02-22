import os
import re
import duckdb
import pandas as pd
from typing import List
from .duckdb_manager import DuckDBManager
from tqdm import tqdm

class ParquetCacheManager:
    def __init__(self):
        self.manager = DuckDBManager.get_instance()
        self.csv_dir = os.getenv("DATASOURCE_FOLDER")
        self.data_dir = os.getenv("DATA_DIR", "data")
        self.db_path = os.path.join(self.data_dir, "raw.duckdb")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.con = duckdb.connect(database=self.db_path)
        self._create_raw_table()

    def _create_raw_table(self):
        self.con.execute("""
        CREATE TABLE IF NOT EXISTS floorsheet (
            symbol VARCHAR,
            business_date DATE,
            contract_id VARCHAR,
            quantity BIGINT,
            rate DOUBLE,
            amount DOUBLE,
            buyer_broker VARCHAR,
            seller_broker VARCHAR,
            trade_time TIMESTAMP,
            source VARCHAR
        );
        """)

    def get_csv_files(self, start_date: str = "2023-06-27") -> List[str]:
        files = []
        pattern = re.compile(r"floorsheet_(\d{4}-\d{2}-\d{2})\.csv")
        start_ts = pd.to_datetime(start_date)
        if not self.csv_dir or not os.path.exists(self.csv_dir):
            print(f"Warning: CSV directory {self.csv_dir} does not exist.")
            return []
        for f in os.listdir(self.csv_dir):
            match = pattern.match(f)
            if match:
                file_date = pd.to_datetime(match.group(1))
                if file_date >= start_ts:
                    files.append(os.path.join(self.csv_dir, f))
        return sorted(files)

    def convert_all(self, start_date: str = "2023-06-27"):
        # Check if data already exists
        row_count = self.con.execute("SELECT count(*) FROM floorsheet").fetchone()[0]
        if row_count > 0:
            print(f"floorsheet table already contains {row_count} rows. Skipping CSV conversion.")
            return

        csv_files = self.get_csv_files(start_date)
        print(f"Found {len(csv_files)} CSV files starting from {start_date}")
        for csv_path in tqdm(csv_files, desc="Loading CSVs into DuckDB"):
            self._convert_single(csv_path)

    def _convert_single(self, csv_path: str):
        try:
            query = f"""
                INSERT INTO floorsheet
                SELECT
                    symbol,
                    CAST(business_date AS DATE) AS business_date,
                    contract_id,
                    CAST(quantity AS BIGINT) AS quantity,
                    CAST(rate AS DOUBLE) AS rate,
                    CAST(amount AS DOUBLE) AS amount,
                    buyer_broker,
                    seller_broker,
                    -- CAST(trade_time AS TIMESTAMP) AS trade_time,
                    (CAST(trade_time AS TIMESTAMPTZ) AT TIME ZONE 'UTC')::TIMESTAMP AS trade_time,
                    source
                FROM read_csv_auto('{csv_path}')
                ORDER BY CAST(trade_time AS TIMESTAMP)
            """
            self.con.execute(query)
        except Exception as e:
            print(f"Error loading {csv_path}: {e}")

    def generate_ohlcv(self):
        ohlcv_db_path = os.path.join(self.data_dir, "ohlcv.duckdb")
        print(f"Generating OHLCV tables in {ohlcv_db_path}...")
        
        # Connect to ohlcv.duckdb
        ohlcv_con = duckdb.connect(database=ohlcv_db_path)
        
        # Attach raw database
        ohlcv_con.execute(f"ATTACH '{self.db_path}' AS raw_db")
        
        intervals = {
            '1d': '1 day',
            '1w': '1 week',
            '1m': '1 month'
        }
        
        for name, interval in intervals.items():
            table_name = f"ohlcv_{name}"
            
            # Check if table already exists and has data
            try:
                # If it's a view, we want to replace it anyway
                res = ohlcv_con.execute(f"SELECT count(*) FROM {table_name}").fetchone()
                if res and res[0] > 0:
                    # Check if it's a view or a table
                    tbl_type = ohlcv_con.execute(f"SELECT table_type FROM information_schema.tables WHERE table_name = '{table_name}'").fetchone()
                    if tbl_type and tbl_type[0] == 'BASE TABLE':
                        print(f"{table_name} already exists with {res[0]} rows. Skipping.")
                        continue
            except Exception:
                pass

            print(f"Creating {table_name}...")
            # Drop if exists (could be a view or table)
            ohlcv_con.execute(f"DROP VIEW IF EXISTS {table_name}")
            ohlcv_con.execute(f"DROP TABLE IF EXISTS {table_name}")
            
            query = f"""
            CREATE TABLE {table_name} AS
            SELECT 
                time_bucket(INTERVAL '{interval}', trade_time) AS timestamp,
                symbol AS ticker,
                ARG_MIN(rate, trade_time) AS open,
                MAX(rate) AS high,
                MIN(rate) AS low,
                ARG_MAX(rate, trade_time) AS close,
                SUM(quantity) AS volume,
                ARG_MAX(rate, trade_time) AS price
            FROM raw_db.floorsheet
            GROUP BY timestamp, ticker
            ORDER BY timestamp ASC, ticker ASC
            """
            ohlcv_con.execute(query)
            
        ohlcv_con.execute("DETACH raw_db")
        ohlcv_con.close()
        print("OHLCV generation complete!")

    def merge_all(self):
        print(f"Data is already in DuckDB table floorsheet at {self.db_path}")

    def close(self):
        self.con.close()

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    manager = ParquetCacheManager()
    manager.convert_all()
    manager.merge_all()
    manager.close()