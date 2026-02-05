
import unittest
import pandas as pd
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.datasources.sources import FloorsheetSource, OHLCVSource
from dotenv import load_dotenv

load_dotenv()

class TestNewSources(unittest.TestCase):
    def test_floorsheet_source(self):
        print("\nTesting FloorsheetSource (Raw Data)...")
        source = FloorsheetSource()
        start_time = "2023-06-27"
        end_time = "2023-06-28"
        
        df = source.query(start_time, end_time)
        
        self.assertFalse(df.empty, "Floorsheet dataframe should not be empty")
        
        # Check for columns requested by user (specifically contract_id)
        # Note: The source query uses SELECT *, so check if implementation maps/keeps them
        print("Floorsheet Columns:", df.columns.tolist())
        
        self.assertIn('contract_id', df.columns, "Should contain 'contract_id'")
        self.assertIn('buyer_broker', df.columns, "Should contain 'buyer_broker'")
        
        # Check standard engine columns
        self.assertIn('timestamp', df.columns)
        self.assertIn('ticker', df.columns)
        self.assertIn('price', df.columns)
        
        print(f"Floorsheet Rows: {len(df)}")
        print(df.head(2))

    def test_ohlcv_source(self):
        print("\nTesting OHLCVSource (Aggregated)...")
        source = OHLCVSource()
        start_time = "2023-06-27"
        end_time = "2023-06-28"
        
        df = source.query(start_time, end_time)
        
        self.assertFalse(df.empty, "OHLCV dataframe should not be empty")
        print("OHLCV Columns:", df.columns.tolist())
        
        expected_cols = ['timestamp', 'ticker', 'open', 'high', 'low', 'close', 'volume']
        for col in expected_cols:
            self.assertIn(col, df.columns, f"OHLCV should contain {col}")
            
        print(f"OHLCV Rows: {len(df)}")
        print(df.head(2))

if __name__ == '__main__':
    unittest.main()
