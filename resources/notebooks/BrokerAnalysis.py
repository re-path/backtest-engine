import marimo

__generated_with = "0.19.9"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    from core.datasources import query
    import polars as pl
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import numpy as np

    return go, mo, pl, px, query


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Multi-Broker Preference Dashboard

    This dashboard provides a comprehensive analysis of investment preferences across **all brokers** between **2023-06-27** and **2024-06-27**. We aggregate the top 5 favorite stocks for every broker to identify market-wide trends, individual concentration levels, and "Excellence Multipliers".
    """)
    return


@app.cell
def _(query):
    all_broker_analysis_sql = """
    WITH broker_symbol_totals AS (
        SELECT 
            buyer_broker,
            symbol,
            SUM(amount) as symbol_amount
        FROM raw.floorsheet
        WHERE business_date >= '2023-06-27' AND business_date < '2024-06-27'
        GROUP BY buyer_broker, symbol
    ),
    broker_ranks AS (
        SELECT 
            buyer_broker,
            symbol,
            symbol_amount,
            ROW_NUMBER() OVER (PARTITION BY buyer_broker ORDER BY symbol_amount DESC) as rank
        FROM broker_symbol_totals
    ),
    broker_aggregates AS (
        SELECT 
            buyer_broker,
            SUM(symbol_amount) as total_broker_volume,
            MEDIAN(symbol_amount) as median_symbol_volume
        FROM broker_symbol_totals
        GROUP BY buyer_broker
    )
    SELECT 
        r.buyer_broker,
        r.symbol,
        r.symbol_amount,
        r.rank,
        a.total_broker_volume,
        a.median_symbol_volume
    FROM broker_ranks r
    JOIN broker_aggregates a ON r.buyer_broker = a.buyer_broker
    WHERE r.rank <= 5
    ORDER BY a.total_broker_volume DESC, r.rank ASC
    """
    master_df = query(all_broker_analysis_sql)
    return (master_df,)


@app.cell
def _(master_df, pl):
    metrics_df = master_df.group_by("buyer_broker").agg([
        pl.col("symbol_amount").sum().alias("top_5_volume"),
        pl.col("total_broker_volume").first(),
        pl.col("median_symbol_volume").first(),
        pl.col("symbol_amount").mean().alias("avg_top_5_volume")
    ]).with_columns([
        (pl.col("top_5_volume") / pl.col("total_broker_volume")).alias("concentration_ratio"),
        (pl.col("avg_top_5_volume") / pl.col("median_symbol_volume")).alias("excellence_multiplier")
    ]).sort("total_broker_volume", descending=True)
    return (metrics_df,)


@app.cell(hide_code=True)
def _(metrics_df, mo):
    _top_concentrated = metrics_df.sort("concentration_ratio", descending=True).head(3)
    _most_diversified = metrics_df.sort("concentration_ratio").head(3)

    _high_list = ", ".join([f"Broker {b}" for b in _top_concentrated["buyer_broker"].to_list()])
    _low_list = ", ".join([f"Broker {b}" for b in _most_diversified["buyer_broker"].to_list()])

    _avg_multiplier = metrics_df["excellence_multiplier"].median()

    _summary = f"## Market Insights\n\n"
    _summary += f"Across all brokers, the median **Excellence Multiplier** is **{_avg_multiplier:.1f}x**. This confirms that brokers typically invest significantly more in their top 5 picks than in a representative median stock.\n\n"

    _summary += f"Brokers with the **highest concentration** (most biased toward favorites) include: **{_high_list}**. "
    _summary += f"In contrast, brokers like **{_low_list}** maintain the most **diversified** portfolios relative to the rest of the market.\n\n"

    _summary += "The typical broker deploys approximately **" + f"{metrics_df['concentration_ratio'].median()*100:.1f}%" + "** of their capital into just their top 5 favorite symbols."

    mo.md(_summary)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Hierarchy of Preferences (Sunburst)

    This chart visualizes the share of total market volume held by each broker, partitioned by their top 5 stock preferences.
    """)
    return


@app.cell
def _(master_df, px):
    fig_sunburst = px.sunburst(
        master_df.to_pandas(),
        path=['buyer_broker', 'symbol'],
        values='symbol_amount',
        title="Broker Investment Hierarchy: Top 5 Stocks",
        template="plotly_dark",
        color='symbol_amount',
        color_continuous_scale='Viridis'
    )
    fig_sunburst.update_layout(height=800)
    fig_sunburst
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Most Favored Symbols Across All Brokers

    Which stocks appear most frequently in the "Top 5" list across all brokers?
    """)
    return


@app.cell
def _(master_df, pl, px):
    popularity_df = master_df.group_by("symbol").agg(
        pl.count().alias("times_in_top_5")
    ).sort("times_in_top_5", descending=True).head(15)

    fig_popularity = px.bar(
        popularity_df,
        x="symbol",
        y="times_in_top_5",
        title="Top 15 Most Common 'Favorite' Stocks Across Brokers",
        template="plotly_dark",
        color="times_in_top_5",
        color_continuous_scale="Plasma"
    )
    fig_popularity
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Concentration vs. Excellence Multiplier

    Analyzing the relationship between how concentrated a broker is and how much they "over-weight" their favorites compared to their median pick.
    """)
    return


@app.cell
def _(metrics_df, px):
    fig_bubble = px.scatter(
        metrics_df,
        x="concentration_ratio",
        y="excellence_multiplier",
        size="total_broker_volume",
        color="buyer_broker",
        hover_name="buyer_broker",
        title="Concentration vs. Excellence Multiplier (Bubble Size = Total Volume)",
        labels={
            "concentration_ratio": "Concentration (Top 5 / Total)",
            "excellence_multiplier": "Excellence Multiplier (Top 5 Avg / Median)"
        },
        template="plotly_dark",
        log_y=True
    )
    fig_bubble
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Global Concentration Heatmap

    Ranking brokers by their total volume and visualizing their concentration levels.
    """)
    return


@app.cell
def _(metrics_df, px):
    fig_heatmap = px.bar(
        metrics_df.head(40),
        x="buyer_broker",
        y="concentration_ratio",
        color="excellence_multiplier",
        title="Top 40 Brokers by Volume: Concentration Ratio & Excellence Multiplier",
        template="plotly_dark",
        labels={"concentration_ratio": "Ratio of Top 5 to Total Volume"},
        color_continuous_scale="RdBu_r"
    )
    fig_heatmap.update_layout(xaxis={'categoryorder':'total descending'})
    fig_heatmap
    return


@app.cell
def _():
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # III. Scientific Broker Classification

    This section provides a data-driven taxonomy of brokers based on **18 distinct behavioral dimensions**. We use percentile distributions to assign characteristics, ensuring the classification is relative to current market participants and rigorously scientific.

    ### Classification Methodology & Behavioral Signals

    To classify brokers with scientific rigor, we analyze the following 18 dimensions. Each dimension is mapped to a percentile rank ($P_{rank}$) across the entire broker population for the period of **2023-06-27** to **2024-06-27**:

    1.  **Concentration (HHI):** Portfolio bias; Specialist ($P_{rank} > 0.8$) vs. Generalist ($P_{rank} < 0.2$).
    2.  **Institutional Profile (Mean Trade Size):** Large-block capability vs. retail-level fragmentation.
    3.  **Dawn Striker Bias:** Early-session momentum seeking.
    4.  **Sunset Trader Bias:** End-of-day institutional flow or NAV management.
    5.  **Lunch Time Player:** Mid-day execution during low-volatility windows.
    6.  **Blue Chip Maximalist:** Preference for high-liquidity, market-leading scrips.
    7.  **Speculative Hunter:** Preference for illiquid, high-alpha "Ghost" scrips.
    8.  **Retail Fragmenter:** Frequency of trades involving fewer than 100 shares.
    9.  **High Velocity:** Numerical intensity of trades per active day.
    10. **Market Stayer:** Temporal consistency of market participation.
    11. **Accumulator / Distributor:** Directional inventory bias (Net Buy vs. Net Sell).
    12. **Closed Circle Trader:** High counterparty concentration (Cross-trading signals).
    13. **Portfolio Explorer:** Active search for new symbols relative to total volume.
    14. **Day Trading Machine:** Gross-to-net volume churning (high intraday turnover).
    15. **Market Making Force:** Dominant contribution to total market share.
    16. **Seasonal Veteran:** Long-term temporal stability across the analysis range.
    17. **Breadth Seeker:** Raw diversity of distinct symbols traded.
    18. **Diversity Index:** Structural complexity of the scrip-volume distribution.

    ### Behavioral Archetypes & Signal Interpretation

    The assigned characteristics (tags) provide meaningful signals for trade interpretation:

    *   **`HYPER_CONCENTRATED`**: Focuses capital on 1-2 symbols. Indicates **High Conviction** or insider-driven strategy. Signal: Extremely strong bias in a specific scrip.
    *   **`ULTRA_DIVERSIFIED`**: Spreads capital broadly. Representative of **Index Funds** or broad-market allocators. Signal: Passive, non-directional market participation.
    *   **`INSTITUTIONAL_WHALE`**: Executes high-value block trades. Signal: **Institutional Entry/Exit** points; follow these as structural support/resistance levels.
    *   **`R_FRAGMENT_COLLECTOR`**: High volume of tiny trades. Signal: **Retail Interest** or high-frequency order-splitting.
    *   **`DAWN_STRIKER`**: Aggressive entries in the first 45 minutes. Signal: **Information Arbitrage**; reacting to news before the pack.
    *   **`SUNSET_TRADER`**: Trades in the final 30 minutes. Signal: **Institutional Window Dressing** or end-of-day position squared-off.
    *   **`LUNCH_TIME_PLAYER`**: Trades during low-liquidity mid-day. Signal: **Patient Execution**; using algorithms to avoid market impact.
    *   **`BLUE_CHIP_MAXIMALIST`**: Sticks to market leaders. Signal: **Conservative Risk Appetite**; seeking stability over alpha.
    *   **`SPECULATIVE_HUNTER`**: Targets illiquid "ghost" stocks. Signal: **High-Alpha Seeking** or potential "Cornering" in small-cap scrips.
    *   **`FRAGMENT_TRADER`**: High frequency of micro-trades. Signal: **Algorithmic Liquidity Provision** or retail aggregation.
    *   **`HIGH_VELOCITY`**: Executes hundreds of trades daily. Signal: **Active Intraday Management**; high sensitivity to short-term fluctuations.
    *   **`MARKET_STAYER`**: Present almost every market day. Signal: **Persistent Liquidity**; a pillar of market stability.
    *   **`ACCUMULATOR` / `DISTRIBUTOR`**: Signals **Net Inflow/Outflow**. An `ACCUMULATOR` is actively building a position; a `DISTRIBUTOR` is unloading.
    *   **`CLOSED_CIRCLE_TRADER`**: Trades with very few counterparties. Signal: **Potential Cross-Trading** or strategic internal transfers.
    *   **`PORTFOLIO_EXPLORER`**: High turnover of symbol list. Signal: **Systematic Scouting** for new opportunities.
    *   **`DAY_TRADING_MACHINE`**: High volume with zero net position. Signal: **Churn-Driven Strategy**; providing liquidity without taking directional risk.
    *   **`MARKET_MAKING_FORCE`**: Highest market share. Signal: **Trend Definition**; their orders *are* the market's momentum.
    *   **`SEASONAL_VETERAN`**: Active across all months. Signal: **Fundamental Presence**; long-term commitment to the market.
    *   **`BREADTH_SEEKER`**: Trades almost every symbol in the market. Signal: **Universal Broker** behavior; likely representing a diverse institutional desk.
    """)
    return


@app.cell
def _(query):
    classification_sql = """
    WITH market_scrip_stats AS (
        SELECT 
            symbol,
            SUM(amount) as scrip_turnover
        FROM raw.floorsheet
        WHERE business_date >= '2023-06-27' AND business_date < '2024-06-27'
        GROUP BY symbol
    ),
    market_ranks AS (
        SELECT 
            symbol,
            PERCENT_RANK() OVER (ORDER BY scrip_turnover) as turnover_rank
        FROM market_scrip_stats
    ),
    leadership_scripts AS (SELECT symbol FROM market_ranks WHERE turnover_rank >= 0.90),
    ghost_scripts AS (SELECT symbol FROM market_ranks WHERE turnover_rank <= 0.20),

    broker_metrics AS (
        SELECT 
            buyer_broker as broker,
            SUM(amount) as total_buy_vol,
            COUNT(*) as trade_count,
            COUNT(DISTINCT business_date) as active_days,
            COUNT(DISTINCT symbol) as unique_symbols,
            COUNT(DISTINCT strftime('%Y-%m', business_date)) as active_months,
            SUM(CASE WHEN CAST(trade_time AS TIME) < '11:45:00' THEN amount ELSE 0 END) / NULLIF(SUM(amount), 0) as early_pct,
            SUM(CASE WHEN CAST(trade_time AS TIME) > '14:30:00' THEN amount ELSE 0 END) / NULLIF(SUM(amount), 0) as late_pct,
            SUM(CASE WHEN CAST(trade_time AS TIME) BETWEEN '12:30:00' AND '13:30:00' THEN amount ELSE 0 END) / NULLIF(SUM(amount), 0) as midday_pct,
            SUM(CASE WHEN symbol IN (SELECT symbol FROM leadership_scripts) THEN amount ELSE 0 END) / NULLIF(SUM(amount), 0) as leader_pct,
            SUM(CASE WHEN symbol IN (SELECT symbol FROM ghost_scripts) THEN amount ELSE 0 END) / NULLIF(SUM(amount), 0) as ghost_pct,
            SUM(CASE WHEN quantity < 100 THEN 1 ELSE 0 END) * 1.0 / NULLIF(COUNT(*), 0) as retail_pct,
            SUM(amount) / NULLIF(COUNT(*), 0) as avg_trade_size,
            COUNT(*) * 1.0 / NULLIF(COUNT(DISTINCT business_date), 0) as trades_per_day
        FROM raw.floorsheet
        WHERE business_date >= '2023-06-27' AND business_date < '2024-06-27'
        GROUP BY buyer_broker
    ),

    seller_stats AS (
        SELECT 
            seller_broker as broker,
            SUM(amount) as total_sell_vol
        FROM raw.floorsheet
        WHERE business_date >= '2023-06-27' AND business_date < '2024-06-27'
        GROUP BY seller_broker
    ),

    hhi_base AS (
        SELECT 
            buyer_broker as broker,
            SUM(POWER(amount, 2)) / POWER(SUM(amount), 2) as hhi
        FROM raw.floorsheet
        WHERE business_date >= '2023-06-27' AND business_date < '2024-06-27'
        GROUP BY buyer_broker
    ),

    cp_stats AS (
        SELECT 
            buyer_broker as broker,
            seller_broker as cp,
            SUM(amount) as cp_amount
        FROM raw.floorsheet
        WHERE business_date >= '2023-06-27' AND business_date < '2024-06-27'
        GROUP BY buyer_broker, seller_broker
    ),
    cp_hhi AS (
        SELECT 
            broker,
            SUM(POWER(cp_amount, 2)) / POWER(SUM(cp_amount), 2) as cp_hhi
        FROM cp_stats
        GROUP BY broker
    )

    SELECT 
        bm.*,
        ss.total_sell_vol,
        h.hhi,
        c.cp_hhi,
        (bm.total_buy_vol - COALESCE(ss.total_sell_vol, 0)) / (bm.total_buy_vol + COALESCE(ss.total_sell_vol, 0)) as inventory_bias,
        (bm.total_buy_vol + COALESCE(ss.total_sell_vol, 0)) / NULLIF(ABS(bm.total_buy_vol - COALESCE(ss.total_sell_vol, 0)), 0) as day_trade_intensity,
        bm.total_buy_vol / (SELECT SUM(amount) FROM raw.floorsheet WHERE business_date >= '2023-06-27' AND business_date < '2024-06-27') as market_share,
        bm.unique_symbols / LOG10(NULLIF(bm.total_buy_vol, 0) + 1) as diversity_index
    FROM broker_metrics bm
    LEFT JOIN seller_stats ss ON bm.broker = ss.broker
    LEFT JOIN hhi_base h ON bm.broker = h.broker
    LEFT JOIN cp_hhi c ON bm.broker = c.broker
    """
    raw_classification_df = query(classification_sql)
    return (raw_classification_df,)


@app.cell
def _(pl, raw_classification_df):
    def get_percentile_rank(df, col):
        return df.select(
            pl.col(col).rank(descending=False) / pl.count()
        ).to_series()

    cols_to_rank = [
        "hhi", "avg_trade_size", "early_pct", "late_pct", "midday_pct",
        "leader_pct", "ghost_pct", "retail_pct", "trades_per_day",
        "active_days", "inventory_bias", "cp_hhi", "diversity_index",
        "day_trade_intensity", "market_share", "active_months", "unique_symbols"
    ]

    ranked_df = raw_classification_df.clone()
    for col in cols_to_rank:
        ranked_df = ranked_df.with_columns([
            get_percentile_rank(raw_classification_df, col).alias(f"{col}_rank")
        ])
    return (ranked_df,)


@app.cell
def _(pl, ranked_df):
    def assign_tags(row):
        tags = []
        if row["hhi_rank"] > 0.8: tags.append("HYPER_CONCENTRATED")
        if row["hhi_rank"] < 0.2: tags.append("ULTRA_DIVERSIFIED")
        if row["avg_trade_size_rank"] > 0.9: tags.append("INSTITUTIONAL_WHALE")
        if row["avg_trade_size_rank"] < 0.2: tags.append("R_FRAGMENT_COLLECTOR")
        if row["early_pct_rank"] > 0.8: tags.append("DAWN_STRIKER")
        if row["late_pct_rank"] > 0.8: tags.append("SUNSET_TRADER")
        if row["midday_pct_rank"] > 0.8: tags.append("LUNCH_TIME_PLAYER")
        if row["leader_pct_rank"] > 0.8: tags.append("BLUE_CHIP_MAXIMALIST")
        if row["ghost_pct_rank"] > 0.8: tags.append("SPECULATIVE_HUNTER")
        if row["retail_pct_rank"] > 0.8: tags.append("FRAGMENT_TRADER")
        if row["trades_per_day_rank"] > 0.8: tags.append("HIGH_VELOCITY")
        if row["active_days_rank"] > 0.9: tags.append("MARKET_STAYER")
        if row["inventory_bias_rank"] > 0.8: tags.append("ACCUMULATOR")
        if row["inventory_bias_rank"] < 0.2: tags.append("DISTRIBUTOR")
        if row["cp_hhi_rank"] > 0.8: tags.append("CLOSED_CIRCLE_TRADER")
        if row["diversity_index_rank"] > 0.8: tags.append("PORTFOLIO_EXPLORER")
        if row["day_trade_intensity_rank"] > 0.8: tags.append("DAY_TRADING_MACHINE")
        if row["market_share_rank"] > 0.9: tags.append("MARKET_MAKING_FORCE")
        if row["active_months_rank"] > 0.9: tags.append("SEASONAL_VETERAN")
        if row["unique_symbols_rank"] > 0.8: tags.append("BREADTH_SEEKER")

        return " | ".join(tags) if tags else "NORMAL_TRADER"

    profile_df = ranked_df.with_columns([
        pl.struct(ranked_df.columns).map_elements(assign_tags, return_dtype=pl.String).alias("CHARACTERISTICS")
    ])
    return (profile_df,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Global Behavioral Profile (Parallel Coordinates)

    This chart compares all brokers across the 18+ dimensions simultaneously. Each line represents a broker, and its position on the vertical axes shows its percentile rank in that dimension.
    """)
    return


@app.cell
def _(profile_df, px):
    _pc_cols = [c for c in profile_df.columns if c.endswith("_rank")]

    fig_parallel = px.parallel_coordinates(
        profile_df.to_pandas(),
        dimensions=_pc_cols,
        color="total_buy_vol",
        color_continuous_scale=px.colors.diverging.Tealrose,
        title="Scientific Broker Profiling: 18 Parallel Dimensions",
        template="plotly_dark"
    )
    fig_parallel.update_layout(height=700)
    fig_parallel
    return


if __name__ == "__main__":
    app.run()
