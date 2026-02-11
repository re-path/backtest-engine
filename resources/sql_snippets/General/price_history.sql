SELECT time_bucket(INTERVAL '1 day', trade_time) as day, last(rate) as close_price FROM floorsheets WHERE symbol = 'NABIL' GROUP BY day ORDER BY day DESC;
