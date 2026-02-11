"""
Shared pytest fixtures for the backtest-engine test suite.
"""
import pytest
import pandas as pd
import numpy as np
import os
import sys
import tempfile
import shutil

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from core.context import Context, Position, PriceMath


# ---------------------------------------------------------------------------
# Context fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def event_log():
    """A fresh mutable list for capturing Context events."""
    return []


@pytest.fixture
def context(event_log):
    """A Context with deterministic parameters (no slippage, no fees, no delay)."""
    return Context(
        initial_balance=10000.0,
        slippage=0.0,
        event_log=event_log,
        execution_delay=0,
        broker_fee=0.0,
        annual_interest_rate=0.0,
    )


@pytest.fixture
def context_with_slippage(event_log):
    """Context with 1% slippage."""
    return Context(
        initial_balance=10000.0,
        slippage=0.01,
        event_log=event_log,
        execution_delay=0,
        broker_fee=0.0,
    )


@pytest.fixture
def context_with_fees(event_log):
    """Context with 0.5% broker fee."""
    return Context(
        initial_balance=10000.0,
        slippage=0.0,
        event_log=event_log,
        execution_delay=0,
        broker_fee=0.005,
    )


@pytest.fixture
def context_with_delay():
    """Context with 60-second execution delay."""
    log = []
    return Context(
        initial_balance=10000.0,
        slippage=0.0,
        event_log=log,
        execution_delay=60,
        broker_fee=0.0,
    )


# ---------------------------------------------------------------------------
# Event-log DataFrames (simulate engine output)
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_event_log_df():
    """
    A realistic event-log DataFrame with a START event, buys, sells, 
    and a final balance — enough to exercise analyze_portfolio fully.
    """
    timestamps = pd.date_range("2023-01-01", periods=10, freq="D")
    rows = [
        {"timestamp": timestamps[0], "event_type": "START",  "ticker": None,   "price": None,  "money_change": 0.0,     "portfolio_balance": 10000.0},
        {"timestamp": timestamps[1], "event_type": "BUY",    "ticker": "AAPL", "price": 150.0, "money_change": -1500.0, "portfolio_balance": 8500.0},
        {"timestamp": timestamps[2], "event_type": "BUY",    "ticker": "GOOG", "price": 100.0, "money_change": -1000.0, "portfolio_balance": 7500.0},
        {"timestamp": timestamps[3], "event_type": "SELL",   "ticker": "AAPL", "price": 160.0, "money_change": 1600.0,  "portfolio_balance": 9100.0},
        {"timestamp": timestamps[4], "event_type": "BUY",    "ticker": "MSFT", "price": 200.0, "money_change": -2000.0, "portfolio_balance": 7100.0},
        {"timestamp": timestamps[5], "event_type": "SELL",   "ticker": "GOOG", "price": 90.0,  "money_change": 900.0,   "portfolio_balance": 8000.0},
        {"timestamp": timestamps[6], "event_type": "SELL",   "ticker": "MSFT", "price": 220.0, "money_change": 2200.0,  "portfolio_balance": 10200.0},
        {"timestamp": timestamps[7], "event_type": "BUY",    "ticker": "AAPL", "price": 155.0, "money_change": -1550.0, "portfolio_balance": 8650.0},
        {"timestamp": timestamps[8], "event_type": "CLOSE",  "ticker": "AAPL", "price": 140.0, "money_change": 1400.0,  "portfolio_balance": 10050.0},
        {"timestamp": timestamps[9], "event_type": "BUY",    "ticker": "TSLA", "price": 300.0, "money_change": -3000.0, "portfolio_balance": 7050.0},
    ]
    return pd.DataFrame(rows)


@pytest.fixture
def empty_event_log_df():
    """Empty DataFrame with the correct schema."""
    return pd.DataFrame(columns=["timestamp", "event_type", "ticker", "price", "money_change", "portfolio_balance"])


@pytest.fixture
def all_winning_event_log_df():
    """Event log where every trade is profitable."""
    ts = pd.date_range("2023-01-01", periods=5, freq="D")
    rows = [
        {"timestamp": ts[0], "event_type": "START", "ticker": None,   "price": None,  "money_change": 0.0,    "portfolio_balance": 1000.0},
        {"timestamp": ts[1], "event_type": "BUY",   "ticker": "AAA",  "price": 10.0,  "money_change": -100.0, "portfolio_balance": 900.0},
        {"timestamp": ts[2], "event_type": "SELL",  "ticker": "AAA",  "price": 15.0,  "money_change": 150.0,  "portfolio_balance": 1050.0},
        {"timestamp": ts[3], "event_type": "BUY",   "ticker": "BBB",  "price": 20.0,  "money_change": -200.0, "portfolio_balance": 850.0},
        {"timestamp": ts[4], "event_type": "SELL",  "ticker": "BBB",  "price": 30.0,  "money_change": 300.0,  "portfolio_balance": 1150.0},
    ]
    return pd.DataFrame(rows)


@pytest.fixture
def all_losing_event_log_df():
    """Event log where every trade loses money."""
    ts = pd.date_range("2023-01-01", periods=5, freq="D")
    rows = [
        {"timestamp": ts[0], "event_type": "START", "ticker": None,   "price": None,  "money_change": 0.0,    "portfolio_balance": 1000.0},
        {"timestamp": ts[1], "event_type": "BUY",   "ticker": "XXX",  "price": 50.0,  "money_change": -500.0, "portfolio_balance": 500.0},
        {"timestamp": ts[2], "event_type": "SELL",  "ticker": "XXX",  "price": 40.0,  "money_change": 400.0,  "portfolio_balance": 900.0},
        {"timestamp": ts[3], "event_type": "BUY",   "ticker": "YYY",  "price": 30.0,  "money_change": -300.0, "portfolio_balance": 600.0},
        {"timestamp": ts[4], "event_type": "SELL",  "ticker": "YYY",  "price": 20.0,  "money_change": 200.0,  "portfolio_balance": 800.0},
    ]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Mock datasource for engine tests (no DuckDB needed)
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_datasource_func():
    """Returns a datasource function that yields a fixed DataFrame."""
    def _datasource(start_time, end_time):
        start = pd.to_datetime(start_time)
        end = pd.to_datetime(end_time)
        dates = pd.date_range(start=start, end=end - pd.Timedelta(seconds=1), freq="D")
        if len(dates) == 0:
            return pd.DataFrame(columns=["timestamp", "ticker", "price"])
        rows = []
        for d in dates:
            for ticker, price in [("AAPL", 150.0), ("GOOG", 100.0)]:
                rows.append({"timestamp": d, "ticker": ticker, "price": price})
        return pd.DataFrame(rows)
    return _datasource


# ---------------------------------------------------------------------------
# Temporary directory fixtures for file-based tests
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_dir(tmp_path):
    """Provides a temporary directory (pytest built-in tmp_path)."""
    return tmp_path
