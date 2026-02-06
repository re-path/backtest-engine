
import pandas as pd
import os
from .duckdb_manager import DuckDBManager

import glob

class BaseDuckDBSource:
    def __init__(self):
        self.manager = DuckDBManager.get_instance()

    def _get_target_globs(self, start_date, end_date):
        base_path = self.manager.get_base_path()
        target_globs = []
        
        # Create a daily range
        search_dates = pd.date_range(start=start_date.floor('D'), end=end_date.ceil('D'), freq='D')
        
        if len(search_dates) == 0:
            return []

        for date in search_dates:
            y_str = str(date.year)
            m_str = f"{date.month:02d}"
            d_str = f"{date.day:02d}"
            
            # Pattern: .../symbol=*/year=YYYY/month=MM/day=DD/*.csv
            day_glob = os.path.join(
                base_path, 
                "symbol=*", 
                f"year={y_str}", 
                f"month={m_str}", 
                f"day={d_str}", 
                "*.csv"
            )
            
            # Only include globs that actually match files to prevent DuckDB IO errors
            # valid paths will return a non-empty list from glob.glob
            if glob.glob(day_glob):
                target_globs.append(day_glob)
            
        return target_globs

class FloorsheetSource(BaseDuckDBSource):
    def query(self, start_time, end_time):
        start_date = pd.to_datetime(start_time)
        end_date = pd.to_datetime(end_time)
        
        target_globs = self._get_target_globs(start_date, end_date)
        
        if not target_globs:
             return pd.DataFrame()

        # Raw query selecting all columns
        # types={'trade_time': 'TIMESTAMP', 'rate': 'DOUBLE', 'symbol': 'VARCHAR', 'contract_id': 'VARCHAR'}
        # We define contract_id as VARCHAR to stay safe, or BIGINT
        try:
            query = """
                SELECT 
                    * 
                FROM read_csv(?, 
                              hive_partitioning=1, 
                              union_by_name=1, 
                              filename=0,
                              header=1,
                              auto_detect=1,
                              types={'trade_time': 'TIMESTAMP', 'rate': 'DOUBLE', 'symbol': 'VARCHAR'})
                WHERE 
                    trade_time >= ? AND trade_time < ?
                ORDER BY trade_time ASC
            """
            
            df = self.manager.execute(query, [target_globs, start_date, end_date]).df()
            
            if not df.empty:
                # Ensure compatibility with engine expectations by aliasing
                df['timestamp'] = pd.to_datetime(df['trade_time'])
                df['ticker'] = df['symbol']
                df['price'] = df['rate']
                
            return df

        except Exception as e:
            print(f"FloorsheetSource Error: {e}")
            return pd.DataFrame()

class OHLCVSource(BaseDuckDBSource):
    def query(self, start_time, end_time):
        start_date = pd.to_datetime(start_time)
        end_date = pd.to_datetime(end_time)
        
        target_globs = self._get_target_globs(start_date, end_date)
        
        if not target_globs:
             return pd.DataFrame()

        # Aggregated Query
        # We group by symbol and bucket(time)
        # For this implementation, we will act as if we are providing data in the same stream format
        # but just fewer points if it was truly OHLCV.
        # HOWEVER, the user asked for "two sources".
        # If the engine expects a stream of trades, OHLCV source might be for a different use case or
        # the engine needs to handle bars.
        # For the purpose of "Backtest Engine", usually it iterates. 
        # If this source returns 1-minute bars, the engine iterates 1-minute steps.
        
        try:
            # We will generate 1-minute bars for now as a default aggregation
            query = """
                SELECT 
                    time_bucket(INTERVAL '1 minute', trade_time) as timestamp,
                    symbol as ticker,
                    FIRST(rate) as open,
                    MAX(rate) as high,
                    MIN(rate) as low,
                    LAST(rate) as close,
                    SUM(quantity) as volume
                FROM read_csv(?, 
                              hive_partitioning=1, 
                              union_by_name=1, 
                              filename=0,
                              header=1,
                              auto_detect=1,
                              types={'trade_time': 'TIMESTAMP', 'rate': 'DOUBLE', 'symbol': 'VARCHAR'})
                WHERE 
                    trade_time >= ? AND trade_time < ?
                GROUP BY timestamp, ticker
                ORDER BY timestamp ASC
            """
            
            df = self.manager.execute(query, [target_globs, start_date, end_date]).df()
            
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                # Price for the engine to execute on? usually 'close' or 'open' of next bar
                # We map 'price' to 'close' for simple backtest compatibility
                df['price'] = df['close']
                
            return df

        except Exception as e:
            print(f"OHLCVSource Error: {e}")
            return pd.DataFrame()

class ContextualFloorsheetSource(BaseDuckDBSource):
    def __init__(self, lookback_period='1 DAY'):
        super().__init__()
        # Ensure lookback_period is a valid DuckDB interval string, e.g., '1 DAY', '1 MINUTE'
        self.lookback_period = lookback_period

    def query(self, start_time, end_time):
        start_date = pd.to_datetime(start_time)
        end_date = pd.to_datetime(end_time)
        
        # Calculate extended start time to fetch historical data for the lookback
        # We need to subtract the lookback period from the start date (safely handled via SQL or pandas)
        # For simplicity, if it's '1 DAY', we subtract 1 day. 
        # Since we are using glob patterns by Day, we need to ensure we grab enough previous files.
        # We'll use a rough estimate for globs (e.g. subtract 2 days to be safe) or use the exact offset if possible.
        
        # DuckDB interval parsing in Python can be tricky without dedicated lib, 
        # so for file globs, we'll try to be generous.
        glob_start_date = start_date - pd.Timedelta(self.lookback_period)
        
        target_globs = self._get_target_globs(glob_start_date, end_date)
        
        if not target_globs:
             return pd.DataFrame()

        try:
            # We select ALL raw columns from the 'trades' part.
            # We compute previous OHLCV from the *entire* loaded dataset (history + current),
            # then join it to the current window's trades.
            
            # The 'bucket' for the previous stats is simply time_bucket of the trade time minus the period.
            # But in the join, equality is easier: 
            #   OHLCV Bucket = Time_Bucket(Trade Time) - Interval
            #   OR
            #   OHLCV Bucket + Interval = Time_Bucket(Trade Time)
            
            query = f"""
                WITH raw_data AS (
                    SELECT 
                        *,
                        trade_time::TIMESTAMP as ts,
                        symbol as sym
                    FROM read_csv(?, 
                                hive_partitioning=1, 
                                union_by_name=1, 
                                filename=0,
                                header=1,
                                auto_detect=1,
                                types={{'trade_time': 'TIMESTAMP', 'rate': 'DOUBLE', 'symbol': 'VARCHAR'}})
                ),
                
                stats AS (
                    SELECT 
                        time_bucket(INTERVAL '{self.lookback_period}', ts) as bucket,
                        sym,
                        FIRST(rate) as prev_open,
                        MAX(rate) as prev_high,
                        MIN(rate) as prev_low,
                        LAST(rate) as prev_close,
                        SUM(quantity) as prev_volume
                    FROM raw_data
                    GROUP BY bucket, sym
                )
                
                SELECT 
                    r.*,
                    s.prev_open,
                    s.prev_high,
                    s.prev_low,
                    s.prev_close,
                    s.prev_volume
                FROM raw_data r
                LEFT JOIN stats s 
                    ON r.sym = s.sym 
                    AND (time_bucket(INTERVAL '{self.lookback_period}', r.ts) = s.bucket + INTERVAL '{self.lookback_period}')
                WHERE 
                    r.ts >= ? AND r.ts < ?
                ORDER BY r.ts ASC
            """
            
            # Note: We pass start_date (original) to the WHERE clause to only return requested trades,
            # but we loaded more data (via target_globs and raw_data) to compute the stats.
            
            params = [target_globs, start_date, end_date]
            df = self.manager.execute(query, params).df()
            
            if not df.empty:
                # Cleanup auxiliary columns if we want, or keep them. 
                # The user asked for "each of the row will have the previous day's ohlcv"
                # 'ts' and 'sym' were aliases, we can drop them or leave them.
                # Usually better to clean up.
                if 'ts' in df.columns: del df['ts']
                if 'sym' in df.columns: del df['sym']
                
                # Standardize
                df['timestamp'] = pd.to_datetime(df['trade_time'])
                df['ticker'] = df['symbol']
                df['price'] = df['rate']

            return df

        except Exception as e:
            print(f"ContextualFloorsheetSource Error: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

