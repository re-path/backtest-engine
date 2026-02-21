from core.datasources import query
df = query("""
    SELECT * 
    FROM floorsheet 
    WHERE ticker = {{ ticker }} 
    ORDER BY timestamp DESC 
    LIMIT 100
""", ticker='SCB')
print(df)
