
import pandas as pd
import os
from .duckdb_manager import DuckDBManager

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
