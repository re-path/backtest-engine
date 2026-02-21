import marimo

__generated_with = "0.19.9"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    from core.datasources import query
    import polars as pl
    import plotly.express as px

    return mo, px, query


@app.cell
def _(query):
    all_stocks = query("""
    WITH min_all_time AS (
        SELECT date_trunc('d', min(trade_time)) AS min_all_time FROM raw.floorsheet
    )
    SELECT symbol, min(trade_time) AS min_trade_time FROM raw.floorsheet GROUP BY symbol 
    HAVING date_trunc('d', min_trade_time) != (SELECT min_all_time FROM min_all_time)
    """)
    all_stocks
    return (all_stocks,)


@app.cell
def _(query):
    query("SELECT * FROM raw.floorsheet LIMIT 5")
    return


@app.cell(hide_code=True)
def _(all_stocks, mo):
    stock = mo.ui.dropdown(
        options=all_stocks['symbol'].sort().to_list(),
        label="Select Stock"
    )
    stock
    return (stock,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Idk what is the reason but it seems like for some of the stocks it is not giving the IPO date it seems like.

    `MEL`  does seem to have the IPO date
    """)
    return


@app.cell
def _(px, query, stock):
    _df = query(f"""

    WITH d1 AS (
        SELECT symbol, trade_time, strftime(business_date, '%A') AS day, quantity, rate, amount, buyer_broker, seller_broker FROM raw.floorsheet 
            WHERE symbol = '{stock.value}'
        ORDER BY trade_time
    ),

    d2 AS (
        SELECT 
            trade_time,
            (trade_time - lag(trade_time, 1) OVER (PARTITION BY symbol ORDER BY trade_time)) AS diff 
        FROM d1
        WHERE date_trunc('d', trade_time) < (
                    date_trunc('d', (SELECT min(trade_time) FROM d1)) + INTERVAL 1 DAY
                )
    )

    SELECT *, epoch_us(diff) AS diff_us FROM d2

    """)

    _pdf = _df.to_pandas()
    _fig = px.scatter(_pdf, x="trade_time", y="diff_us",
                     title="Scatter of diff over trade_time", opacity=0.3,
                     labels={"trade_time": "Trade Time", "diff": "Diff"})
    _fig.show()
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
