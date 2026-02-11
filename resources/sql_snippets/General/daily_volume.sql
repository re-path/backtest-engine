SELECT time_bucket(INTERVAL '1 day', trade_time) as day, sum(quantity) as volume FROM floorsheets GROUP BY day ORDER BY day DESC;
