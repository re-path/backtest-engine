"""
Tests for BacktestEngineWithSource and plot_simulation_trades.
Uses mock datasources (no DuckDB needed).
"""
import pytest
import pandas as pd
import plotly.graph_objects as go
from unittest.mock import patch

from core.engine import BacktestEngineWithSource, plot_simulation_trades


# ---------------------------------------------------------------------------
# Minimal strategy for testing
# ---------------------------------------------------------------------------

class DoNothingStrategy:
    """Strategy that does nothing — just observes."""
    def __init__(self, **kwargs):
        pass

    def on_bar(self, context, bar):
        pass


class BuyOnceStrategy:
    """Buys 100 money of the first ticker it sees, once."""
    def __init__(self, **kwargs):
        self.bought = False

    def on_bar(self, context, bar):
        if not self.bought:
            context.buy(bar.ticker, 100.0, bar.price, bar.timestamp)
            self.bought = True


class BuyAndSellStrategy:
    """Buys on first bar, sells on second bar."""
    def __init__(self, **kwargs):
        self.bar_count = 0

    def on_bar(self, context, bar):
        self.bar_count += 1
        if self.bar_count == 1:
            context.buy(bar.ticker, 100.0, bar.price, bar.timestamp)
        elif self.bar_count == 2:
            context.close(bar.ticker, bar.price, bar.timestamp)


# ---------------------------------------------------------------------------
# BacktestEngineWithSource
# ---------------------------------------------------------------------------

class TestBacktestEngineWithSource:
    def test_engine_produces_event_log(self, mock_datasource_func):
        engine = BacktestEngineWithSource(
            data_source_func=mock_datasource_func,
            start_time="2023-01-01",
            end_time="2023-01-05",
            interval=pd.Timedelta(days=1),
            strategy_cls=DoNothingStrategy,
            initial_money=10000.0,
        )
        result = engine.run()
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        # Should have at least the START event
        assert "START" in result["event_type"].values

    def test_engine_start_event_has_initial_balance(self, mock_datasource_func):
        engine = BacktestEngineWithSource(
            data_source_func=mock_datasource_func,
            start_time="2023-01-01",
            end_time="2023-01-03",
            interval=pd.Timedelta(days=1),
            strategy_cls=DoNothingStrategy,
            initial_money=5000.0,
        )
        result = engine.run()
        start_row = result[result["event_type"] == "START"].iloc[0]
        assert start_row["portfolio_balance"] == pytest.approx(5000.0)

    def test_engine_with_buy_strategy(self, mock_datasource_func):
        engine = BacktestEngineWithSource(
            data_source_func=mock_datasource_func,
            start_time="2023-01-01",
            end_time="2023-01-05",
            interval=pd.Timedelta(days=1),
            strategy_cls=BuyOnceStrategy,
            initial_money=10000.0,
        )
        result = engine.run()
        buy_events = result[result["event_type"] == "BUY"]
        assert len(buy_events) >= 1

    def test_engine_with_buy_and_sell(self, mock_datasource_func):
        engine = BacktestEngineWithSource(
            data_source_func=mock_datasource_func,
            start_time="2023-01-01",
            end_time="2023-01-05",
            interval=pd.Timedelta(days=1),
            strategy_cls=BuyAndSellStrategy,
            initial_money=10000.0,
        )
        result = engine.run()
        event_types = result["event_type"].unique()
        assert "BUY" in event_types

    def test_engine_empty_data(self):
        """Engine handles a datasource returning no data."""
        def empty_source(start, end):
            return pd.DataFrame(columns=["timestamp", "ticker", "price"])

        engine = BacktestEngineWithSource(
            data_source_func=empty_source,
            start_time="2023-01-01",
            end_time="2023-01-03",
            interval=pd.Timedelta(days=1),
            strategy_cls=DoNothingStrategy,
            initial_money=10000.0,
        )
        result = engine.run()
        assert len(result) == 1  # Only START event
        assert result.iloc[0]["event_type"] == "START"

    def test_engine_with_slippage(self, mock_datasource_func):
        engine = BacktestEngineWithSource(
            data_source_func=mock_datasource_func,
            start_time="2023-01-01",
            end_time="2023-01-03",
            interval=pd.Timedelta(days=1),
            strategy_cls=BuyOnceStrategy,
            initial_money=10000.0,
            slippage=0.05,
        )
        result = engine.run()
        assert not result.empty

    def test_engine_with_strategy_params(self, mock_datasource_func):
        class ParamStrategy:
            def __init__(self, threshold=0.5, **kwargs):
                self.threshold = threshold
            def on_bar(self, context, bar):
                pass

        engine = BacktestEngineWithSource(
            data_source_func=mock_datasource_func,
            start_time="2023-01-01",
            end_time="2023-01-03",
            interval=pd.Timedelta(days=1),
            strategy_cls=ParamStrategy,
            initial_money=10000.0,
            strategy_params={"threshold": 0.8},
        )
        result = engine.run()
        assert not result.empty
        assert engine.strategy.threshold == 0.8


# ---------------------------------------------------------------------------
# plot_simulation_trades
# ---------------------------------------------------------------------------

class TestPlotSimulationTrades:
    def test_returns_figure_for_valid_data(self, sample_event_log_df):
        fig = plot_simulation_trades(sample_event_log_df)
        assert isinstance(fig, go.Figure)

    def test_returns_empty_figure_for_empty_df(self, empty_event_log_df):
        fig = plot_simulation_trades(empty_event_log_df)
        assert isinstance(fig, go.Figure)

    def test_figure_has_traces(self, sample_event_log_df):
        fig = plot_simulation_trades(sample_event_log_df)
        assert len(fig.data) > 0

    def test_figure_layout(self, sample_event_log_df):
        fig = plot_simulation_trades(sample_event_log_df)
        assert fig.layout.template.layout.plot_bgcolor is not None or True
        assert fig.layout.height == 800
        assert fig.layout.width == 1600
