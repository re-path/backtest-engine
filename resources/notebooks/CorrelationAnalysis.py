import marimo

__generated_with = "0.19.9"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    from core.datasources import query

    return (query,)


@app.cell
def _(query):
    # No need to manually attach anymore, query() handles it
    # query("SELECT * FROM floorsheet LIMIT 5")
    return


@app.cell
def _(query):
    query("""SELECT distinct symbol FROM raw.floorsheet""")
    return


@app.cell
def _(query):
    query("""
    SHOW tables from 
    """)
    return


if __name__ == "__main__":
    app.run()
