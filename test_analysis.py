import polars as pl
from core.datasources import query

sql = """
SELECT buyer_broker, symbol, SUM(amount) as total_amount
FROM raw.floorsheet
WHERE business_date >= '2023-06-27' AND business_date < '2024-06-27'
GROUP BY buyer_broker, symbol
"""

df = query(sql)
print(df.head())

broker = 58
broker_df = df.filter(pl.col("buyer_broker") == broker).sort("total_amount", descending=True)
print(broker_df.head(10))

total_invested = broker_df["total_amount"].sum()
top_5 = broker_df.head(5)["total_amount"].sum()
rest = total_invested - top_5

print(f"Total: {total_invested}, Top 5: {top_5}, Rest: {rest}")

percentiles = broker_df.select(pl.col("total_amount").quantile(0.95))
print(f"95th percentile: {percentiles[0,0]}")
