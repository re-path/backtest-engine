import pandas as pd
from core.engine import duckdb_datasource

print("Testing duckdb_datasource...")
try:
    df = duckdb_datasource("2023-06-27", "2023-06-28")
    print(f"Result DataFrame Shape: {df.shape}")
    if not df.empty:
        print("Columns:", df.columns.tolist())
        print(df.head())
    else:
        print("DataFrame is empty!")
except Exception as e:
    print(f"Error: {e}")
