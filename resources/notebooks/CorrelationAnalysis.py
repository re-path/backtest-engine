import marimo

__generated_with = "0.19.9"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        SELECT 
            * 
        FROM read_csv('/home/ksai/dev/repath/floorsheet-data/data/floorsheets/symbol=ADBL/year=*/month=*/day=*/*.csv', 
                      hive_partitioning=1, 
                      union_by_name=1, 
                      filename=0,
                      header=1,
                      auto_detect=1)
        WHERE 
            -- Partition pruning (Fast)
            year = '2025' AND month = '01' AND (day = '01' OR day = '02')
            -- Precise filter (On records)
            AND trade_time >= '2025-01-01' AND trade_time < '2025-01-03'
        ORDER BY trade_time ASC
        """
    )
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
