from core.datasources import query
df = query("""
    SELECT 
        timestamp, 
        close as price 
    FROM ohlcv.all_day 
    WHERE ticker = {{ ticker }} 
    ORDER BY timestamp DESC
""", ticker='NABIL')
print(df.head())
