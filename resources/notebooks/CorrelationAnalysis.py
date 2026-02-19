import marimo

__generated_with = "0.19.9"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    from core.datasources import query

    return mo, query


@app.cell
def _(query):
    df = query("""
        SELECT 
            * 
        FROM raw.floorsheet 
        WHERE ticker = '{{ ticker }}'
          AND timestamp >= '{{ start }}' 
          AND timestamp < '{{ end }}'
        ORDER BY timestamp ASC
    """, ticker='ADBL', start='2025-01-01', end='2025-01-03')
    return (df,)


@app.cell
def _(df, mo):
    mo.md(f"""
    ### Data Loaded: {len(df)} records
    """)
    return


@app.cell
def _(df):
    df.head()
    return


@app.cell
def _(query):
    query("""
    SHOW tables from 
    """)
    return


if __name__ == "__main__":
    app.run()
