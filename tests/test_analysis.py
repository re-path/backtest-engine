"""
Unit tests for analyze_portfolio from core/analysis.py.
"""
import pytest
import pandas as pd
from core.analysis import analyze_portfolio


class TestAnalyzePortfolioEmpty:
    def test_returns_none_for_empty_df(self, empty_event_log_df):
        result = analyze_portfolio(empty_event_log_df)
        assert result is None


class TestAnalyzePortfolioBasic:
    def test_returns_dataframe(self, sample_event_log_df):
        result = analyze_portfolio(sample_event_log_df)
        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1

    def test_start_and_end_balance(self, sample_event_log_df):
        result = analyze_portfolio(sample_event_log_df)
        row = result.iloc[0]
        assert row["start_balance"] == pytest.approx(10000.0)
        assert row["end_balance"] == pytest.approx(7050.0)

    def test_total_return_pct(self, sample_event_log_df):
        result = analyze_portfolio(sample_event_log_df)
        row = result.iloc[0]
        expected_pct = (7050.0 / 10000.0 - 1) * 100
        assert row["total_return_pct"] == pytest.approx(expected_pct)

    def test_metric_keys_present(self, sample_event_log_df):
        result = analyze_portfolio(sample_event_log_df)
        row = result.iloc[0]
        expected_keys = [
            "start_balance", "end_balance", "total_return_pct",
            "total_net_profit", "gross_profit", "gross_loss",
            "profit_factor", "total_trades", "num_winning", "num_losing",
            "avg_trade_net_profit", "avg_winning_trade", "avg_losing_trade",
            "largest_winning_trade", "largest_losing_trade",
            "max_consec_winning", "max_consec_losing",
            "max_drawdown_pct", "high_water_mark", "low_water_mark",
        ]
        for key in expected_keys:
            assert key in row.index, f"Missing metric: {key}"

    def test_total_trades_count(self, sample_event_log_df):
        result = analyze_portfolio(sample_event_log_df)
        row = result.iloc[0]
        # Trades are grouped by ticker: AAPL, GOOG, MSFT, TSLA = 4 tickers
        assert row["total_trades"] == 4

    def test_drawdown_fields_present(self, sample_event_log_df):
        result = analyze_portfolio(sample_event_log_df)
        row = result.iloc[0]
        assert "drawdown_depth_money" in row.index
        assert "decline_duration_days" in row.index
        assert "recovery_status_str" in row.index


class TestAnalyzePortfolioAllWinning:
    def test_all_winning_no_losses(self, all_winning_event_log_df):
        result = analyze_portfolio(all_winning_event_log_df)
        row = result.iloc[0]
        assert row["num_losing"] == 0
        assert row["gross_loss"] == pytest.approx(0.0)
        assert row["num_winning"] == 2

    def test_all_winning_profit_factor(self, all_winning_event_log_df):
        result = analyze_portfolio(all_winning_event_log_df)
        row = result.iloc[0]
        # profit_factor = gross_profit / abs(gross_loss); gross_loss=0 → 0.0 per implementation
        assert row["profit_factor"] == pytest.approx(0.0)


class TestAnalyzePortfolioAllLosing:
    def test_all_losing_no_wins(self, all_losing_event_log_df):
        result = analyze_portfolio(all_losing_event_log_df)
        row = result.iloc[0]
        assert row["num_winning"] == 0
        assert row["gross_profit"] == pytest.approx(0.0)
        assert row["num_losing"] == 2

    def test_all_losing_negative_net_profit(self, all_losing_event_log_df):
        result = analyze_portfolio(all_losing_event_log_df)
        row = result.iloc[0]
        assert row["total_net_profit"] < 0


class TestAnalyzePortfolioSingleTrade:
    def test_single_trade(self):
        ts = pd.date_range("2023-01-01", periods=3, freq="D")
        rows = [
            {"timestamp": ts[0], "event_type": "START", "ticker": None,  "price": None, "money_change": 0.0,  "portfolio_balance": 1000.0},
            {"timestamp": ts[1], "event_type": "BUY",   "ticker": "Z",   "price": 10.0, "money_change": -100.0, "portfolio_balance": 900.0},
            {"timestamp": ts[2], "event_type": "SELL",  "ticker": "Z",   "price": 12.0, "money_change": 120.0,  "portfolio_balance": 1020.0},
        ]
        df = pd.DataFrame(rows)
        result = analyze_portfolio(df)
        assert result is not None
        row = result.iloc[0]
        assert row["total_trades"] == 1
        assert row["num_winning"] == 1
