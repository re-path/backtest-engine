
import pandas as pd
import os
import glob
from .duckdb_manager import DuckDBManager
from .preprocessor import SQLPreprocessor

class BaseDuckDBSource:
    def __init__(self):
        self.manager = DuckDBManager.get_instance()
        self.preprocessor = SQLPreprocessor()

    def _get_target_globs(self, start_date, end_date):
        base_path = self.manager.get_base_path()
        target_globs = []
        search_dates = pd.date_range(start=start_date.floor('D'), end=end_date.ceil('D'), freq='D')
        if len(search_dates) == 0:
            return []
        for date in search_dates:
            day_glob = os.path.join(base_path, "symbol=*", f"year={date.year}", f"month={date.month:02d}", f"day={date.day:02d}", "*.csv")
            if glob.glob(day_glob):
                target_globs.append(day_glob)
        return target_globs

class FloorsheetSource(BaseDuckDBSource):
    def query(self, start_time, end_time, ticker="*"):
        try:
            sql = "SELECT * FROM raw.floorsheet WHERE timestamp >= ? AND timestamp < ?"
            params = [pd.to_datetime(start_time), pd.to_datetime(end_time)]
            if ticker != "*":
                sql += " AND ticker = ?"
                params.append(ticker)
            sql += " ORDER BY timestamp ASC"
            return self.manager.execute(sql, params).df()
        except Exception:
            return pd.DataFrame()

class OHLCVSource(BaseDuckDBSource):
    def query(self, start_time, end_time, ticker="*", interval='1 minute'):
        try:
            sql = f"""
                SELECT 
                    time_bucket(INTERVAL '{interval}', timestamp) as timestamp,
                    ticker,
                    FIRST(price) as open,
                    MAX(price) as high,
                    MIN(price) as low,
                    LAST(price) as close,
                    SUM(quantity) as volume,
                    LAST(price) as price
                FROM raw.floorsheet
                WHERE timestamp >= ? AND timestamp < ?
            """
            params = [pd.to_datetime(start_time), pd.to_datetime(end_time)]
            if ticker != "*":
                sql += " AND ticker = ?"
                params.append(ticker)
            sql += " GROUP BY timestamp, ticker ORDER BY timestamp ASC"
            return self.manager.execute(sql, params).df()
        except Exception:
            return pd.DataFrame()

class ContextualFloorsheetSource(BaseDuckDBSource):
    def __init__(self, lookback_period='1 DAY'):
        super().__init__()
        self.lookback_period = lookback_period

    def query(self, start_time, end_time):
        start_date = pd.to_datetime(start_time)
        end_date = pd.to_datetime(end_time)
        try:
            query = f"""
                WITH stats AS (
                    SELECT 
                        time_bucket(INTERVAL '{self.lookback_period}', timestamp) as bucket,
                        ticker,
                        FIRST(price) as prev_open,
                        MAX(price) as prev_high,
                        MIN(price) as prev_low,
                        LAST(price) as prev_close,
                        SUM(quantity) as prev_volume
                    FROM raw.floorsheet
                    GROUP BY bucket, ticker
                )
                SELECT 
                    r.*,
                    s.prev_open, s.prev_high, s.prev_low, s.prev_close, s.prev_volume
                FROM raw.floorsheet r
                LEFT JOIN stats s 
                    ON r.ticker = s.ticker 
                    AND (time_bucket(INTERVAL '{self.lookback_period}', r.timestamp) = s.bucket + INTERVAL '{self.lookback_period}')
                WHERE r.timestamp >= ? AND r.timestamp < ?
                ORDER BY r.timestamp ASC
            """
            return self.manager.execute(query, [start_date, end_date]).df()
        except Exception:
            return pd.DataFrame()

class DailyCloseSource(BaseDuckDBSource):
    def query(self, start_time, end_time):
        try:
            sql = "SELECT timestamp, ticker, close as price FROM ohlcv.all_day WHERE timestamp >= ? AND timestamp < ?"
            return self.manager.execute(sql, [pd.to_datetime(start_time), pd.to_datetime(end_time)]).df()
        except Exception:
            return pd.DataFrame()

class DailyOHLCSource(BaseDuckDBSource):
    def query(self, start_time, end_time):
        try:
            sql = "SELECT * FROM ohlcv.all_day WHERE timestamp >= ? AND timestamp < ?"
            return self.manager.execute(sql, [pd.to_datetime(start_time), pd.to_datetime(end_time)]).df()
        except Exception:
            return pd.DataFrame()
