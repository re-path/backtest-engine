import marimo

__generated_with = "0.19.9"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    from core.datasources import query
    import plotly.express as px

    return mo, query


@app.cell
def _(query):
    all_stocks = query("SELECT DISTINCT ticker FROM ohlcv.ohlcv_1d")
    return (all_stocks,)


@app.cell
def _(all_stocks, mo):
    stock = mo.ui.dropdown(
        options=all_stocks['ticker'].sort().to_list(),
        label="Select Stock"
    )
    stock
    return (stock,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Ohlcv Check
    """)
    return


@app.cell
def _(query, stock):
    ohlcv_data = query(f"""
    SELECT * FROM ohlcv.ohlcv_1d WHERE ticker='{stock.value}'
    """)
    return (ohlcv_data,)


@app.cell
def _(query, stock):
    query(f"SELECT * FROM ohlcv.ohlcv_1d WHERE ticker='{stock.value}' LIMIT 5")
    return


@app.cell(hide_code=True)
def _(ohlcv_data):
    import plotly.graph_objects as go

    fig = go.Figure(data=[go.Candlestick(
        x=ohlcv_data['timestamp'].to_list(),
        open=ohlcv_data['open'].to_list(),
        high=ohlcv_data['high'].to_list(),
        low=ohlcv_data['low'].to_list(),
        close=ohlcv_data['close'].to_list(),
        increasing_line_color='green',
        decreasing_line_color='red'
    )])
    fig.update_layout(xaxis_rangeslider_visible=False)
    fig.show()
    return (go,)


@app.cell(hide_code=True)
def _(go, ohlcv_data):
    _fig = go.Figure(data=[go.Candlestick(
        x=ohlcv_data['timestamp'].to_list(),
        open=ohlcv_data['open'].to_list(),
        high=ohlcv_data['high'].to_list(),
        low=ohlcv_data['low'].to_list(),
        close=ohlcv_data['close'].to_list(),
        increasing_line_color='green',
        decreasing_line_color='red'
    )])
    _fig.update_layout(
        xaxis_type='category',
        xaxis_rangeslider_visible=False
    )
    _fig.show()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Floorsheet Check
    """)
    return


@app.cell
def _(mo, query, stock):
    _df = query(f"""
    WITH d1 AS (
        SELECT symbol,
            trade_time,
            strftime(trade_time, '%A') AS weekday,
            quantity,
            rate,
            amount,
            buyer_broker,
            seller_broker FROM raw.floorsheet 
        WHERE symbol = '{stock.value}'
        ORDER BY trade_time
    ),

    d2 AS (
        SELECT *,
            ((rate - lag(rate, 1) OVER (ORDER BY trade_time)) / rate) AS change,
            epoch_us(trade_time - lag(trade_time, 1) OVER (ORDER BY trade_time)) AS diff_us FROM d1
        WHERE date_trunc('d', trade_time) < date_trunc('d', (SELECT min(trade_time) FROM d1)) + INTERVAL 3 DAY
    ),

    d3 AS (
        SELECT SUM(
           CASE WHEN quantity % 10 != 0 AND quantity < 10
           THEN amount
           ELSE 0
           END
        )  AS sum_odd,
        SUM(amount) AS total_sum
        FROM d2 
    )

     SELECT *, sum_odd/total_sum FROM d3
    -- SELECT * FROM d1

    """)

    # _pdf = _df.to_pandas()
    # _fig = px.scatter(_pdf, x="trade_time", y="diff_us",
    #                  title="Scatter of diff over trade_time", opacity=0.3,
    #                  labels={"trade_time": "Trade Time", "diff": "Diff"})
    mo.output.append(_df)
    # _fig.show()
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
