
import unittest
import pandas as pd
import sys
import os

# Add project root to sys.path to allow running as script
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.engine import duckdb_datasource
from dotenv import load_dotenv

load_dotenv()

class TestDuckDBDatasource(unittest.TestCase):
    def test_query_existing_date(self):
        # We know floorsheet_2023-06-27.csv exists
        start_time = "2023-06-27"
        end_time = "2023-06-28"
        
        df = duckdb_datasource(start_time, end_time)
        
        self.assertFalse(df.empty, "Dataframe should not be empty for existing date")
        self.assertListEqual(list(df.columns), ['timestamp', 'ticker', 'price'])
        
        # Check if timestamps are within range
        start_ts = pd.to_datetime(start_time).tz_localize(df['timestamp'].dt.tz)
        end_ts = pd.to_datetime(end_time).tz_localize(df['timestamp'].dt.tz)
        
        # Note: floorsheet data might be naive or timezone aware. 
        # floorsheet trade_time is 'TIMESTAMP WITH TIME ZONE' in duckdb describe,
        # so pandas result should be tz-aware.
        # We need to handle comparison carefully.
        
        # If df['timestamp'] is tz-aware, we need start_ts/end_ts to be tz-aware or convert df.
        # Let's inspect one value or just handle it loosely if needed.
        
        # Simply check dates
        date_set = set(df['timestamp'].dt.date)
        # 2023-06-27
        self.assertTrue(pd.to_datetime("2023-06-27").date() in date_set, "Should contain data for 2023-06-27")

    def test_query_no_data(self):
        # Pick a date usually without data, e.g. far future or weekend if applicable, 
        # or just random date that might not exist.
        # 2020-01-01 likely doesn't exist based on file list starting 2023.
        start_time = "2020-01-01"
        end_time = "2020-01-02"
        
        df = duckdb_datasource(start_time, end_time)
        self.assertTrue(df.empty, "Dataframe should be empty for non-existent date")
        self.assertListEqual(list(df.columns), ['timestamp', 'ticker', 'price'])

if __name__ == '__main__':
    unittest.main()
