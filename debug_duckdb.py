
import duckdb
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

datasource_folder = os.getenv("DATASOURCE_FOLDER")
base_path = os.path.join(datasource_folder, "floorsheets")


print(f"ENV DATASOURCE_FOLDER: {datasource_folder}")
# Hardcoded known path based on 'find' command success
# /home/ksai/dev/repath/floorsheet-data/data/floorsheets/symbol=*/year=2023/month=06/day=27/*.csv
hardcoded_glob = "/home/ksai/dev/repath/floorsheet-data/data/floorsheets/symbol=*/year=2023/month=06/day=27/*.csv"
print(f"Testing Hardcoded Glob: {hardcoded_glob}")
day_glob = hardcoded_glob


con = duckdb.connect()
con.execute("PRAGMA threads=4")

query = """
    SELECT 
        trade_time,
        symbol,
        rate
    FROM read_csv(?, 
                  hive_partitioning=1, 
                  union_by_name=1, 
                  filename=1,
                  header=1,
                  auto_detect=1)
    LIMIT 5
"""

try:
    # Pass as list [glob]
    df = con.execute(query, [[day_glob]]).df()
    print("Dataframe Result:")
    print(df)
except Exception as e:
    print(f"Error: {e}")
