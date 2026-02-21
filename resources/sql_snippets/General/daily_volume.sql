from core.datasources import query
df = query("""
    SELECT 
        time_bucket(INTERVAL '1 day', timestamp) as day, 
        sum(quantity) as daily_volume 
    FROM floorsheet 
    GROUP BY day 
    ORDER BY day DESC
""")
print(df.head())
