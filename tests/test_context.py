"""
Comprehensive unit tests for the Context class.
Covers state management, buy/sell/close, slippage, fees,
pending orders (execution delay), buy_protected, and load_model.
"""
import pytest
import pickle
import os
import pandas as pd
from core.context import Context, Position


# =========================================================================
# State Management
# =========================================================================

class TestStateManagement:
    def test_set_and_get_state(self, context):
        context.set_state("key1", 42)
        assert context.get_state("key1") == 42

    def test_get_state_default(self, context):
        assert context.get_state("missing") is None
        assert context.get_state("missing", "default") == "default"

    def test_set_get_aliases(self, context):
        context.set("alias_key", [1, 2, 3])
        assert context.get("alias_key") == [1, 2, 3]
        assert context.get("nope", 0) == 0

    def test_overwrite_state(self, context):
        context.set_state("x", 1)
        context.set_state("x", 2)
        assert context.get_state("x") == 2

    def test_state_stores_various_types(self, context):
        context.set_state("int_val", 42)
        context.set_state("str_val", "hello")
        context.set_state("list_val", [1, 2])
        context.set_state("dict_val", {"a": 1})
        assert context.get_state("int_val") == 42
        assert context.get_state("str_val") == "hello"
        assert context.get_state("list_val") == [1, 2]
        assert context.get_state("dict_val") == {"a": 1}


# =========================================================================
# Balance
# =========================================================================

class TestBalance:
    def test_initial_balance(self, context):
        assert context.get_balance() == 10000.0

    def test_balance_property(self):
        log = []
        ctx = Context(999.99, 0.0, log)
        assert ctx.get_balance() == pytest.approx(999.99)


# =========================================================================
# Buy
# =========================================================================

class TestBuy:
    def test_buy_deducts_balance(self, context):
        context.buy("AAPL", 1000.0, 100.0, pd.Timestamp("2023-01-01"))
        assert context.get_balance() == pytest.approx(9000.0)

    def test_buy_creates_position(self, context):
        context.buy("AAPL", 1000.0, 100.0, pd.Timestamp("2023-01-01"))
        pos = context.get_position("AAPL")
        assert pos is not None
        assert pos.share_units == pytest.approx(10.0)  # 1000 / 100

    def test_buy_logs_event(self, context, event_log):
        context.buy("AAPL", 500.0, 50.0, pd.Timestamp("2023-01-01"))
        assert len(event_log) == 1
        assert event_log[0]["event_type"] == "BUY"
        assert event_log[0]["ticker"] == "AAPL"

    def test_buy_returns_shares(self, context):
        shares = context.buy("AAPL", 1000.0, 100.0, pd.Timestamp("2023-01-01"))
        assert shares == pytest.approx(10.0)

    def test_buy_insufficient_funds(self, context):
        shares = context.buy("AAPL", 20000.0, 100.0, pd.Timestamp("2023-01-01"))
        assert shares == 0.0
        assert context.get_balance() == 10000.0  # unchanged
        assert context.get_position("AAPL") is None

    def test_buy_adds_to_existing_position(self, context):
        context.buy("AAPL", 500.0, 100.0, pd.Timestamp("2023-01-01"))
        context.buy("AAPL", 500.0, 100.0, pd.Timestamp("2023-01-02"))
        pos = context.get_position("AAPL")
        assert pos.share_units == pytest.approx(10.0)  # 5 + 5

    def test_buy_tracks_traded_tickers(self, context):
        context.buy("AAPL", 100.0, 10.0, pd.Timestamp("2023-01-01"))
        assert "AAPL" in context.traded_tickers

    def test_buy_multiple_tickers(self, context):
        context.buy("AAPL", 1000.0, 100.0, pd.Timestamp("2023-01-01"))
        context.buy("GOOG", 2000.0, 200.0, pd.Timestamp("2023-01-01"))
        assert context.get_position("AAPL") is not None
        assert context.get_position("GOOG") is not None
        assert context.get_balance() == pytest.approx(7000.0)


# =========================================================================
# Buy with Slippage
# =========================================================================

class TestBuyWithSlippage:
    def test_slippage_increases_buy_price(self, context_with_slippage):
        ctx = context_with_slippage
        shares = ctx.buy("AAPL", 1000.0, 100.0, pd.Timestamp("2023-01-01"))
        # Effective price = 100 * 1.01 = 101
        expected_shares = 1000.0 / 101.0
        assert shares == pytest.approx(expected_shares)

    def test_slippage_deducts_correct_balance(self, context_with_slippage):
        ctx = context_with_slippage
        ctx.buy("AAPL", 1000.0, 100.0, pd.Timestamp("2023-01-01"))
        assert ctx.get_balance() == pytest.approx(9000.0)  # money_amount deducted


# =========================================================================
# Buy with Broker Fee
# =========================================================================

class TestBuyWithFees:
    def test_fee_deducted_on_buy(self, context_with_fees):
        ctx = context_with_fees
        # fee = 1000 * 0.005 = 5; total_cost = 1005
        ctx.buy("AAPL", 1000.0, 100.0, pd.Timestamp("2023-01-01"))
        assert ctx.get_balance() == pytest.approx(10000.0 - 1005.0)

    def test_insufficient_balance_with_fee(self):
        log = []
        ctx = Context(1004.0, 0.0, log, broker_fee=0.005)
        # Need 1005 but only have 1004
        shares = ctx.buy("AAPL", 1000.0, 100.0, pd.Timestamp("2023-01-01"))
        assert shares == 0.0


# =========================================================================
# Sell
# =========================================================================

class TestSell:
    def test_sell_adds_balance(self, context, event_log):
        context.buy("AAPL", 1000.0, 100.0, pd.Timestamp("2023-01-01"))
        money = context.sell("AAPL", 5.0, 120.0, pd.Timestamp("2023-01-02"))
        assert money == pytest.approx(600.0)  # 5 * 120
        assert context.get_balance() == pytest.approx(9000.0 + 600.0)

    def test_sell_reduces_position(self, context):
        context.buy("AAPL", 1000.0, 100.0, pd.Timestamp("2023-01-01"))
        context.sell("AAPL", 3.0, 120.0, pd.Timestamp("2023-01-02"))
        pos = context.get_position("AAPL")
        assert pos is not None
        assert pos.share_units == pytest.approx(7.0)

    def test_sell_removes_position_when_fully_sold(self, context):
        context.buy("AAPL", 1000.0, 100.0, pd.Timestamp("2023-01-01"))
        context.sell("AAPL", 10.0, 120.0, pd.Timestamp("2023-01-02"))
        assert context.get_position("AAPL") is None

    def test_sell_caps_at_position_size(self, context):
        context.buy("AAPL", 1000.0, 100.0, pd.Timestamp("2023-01-01"))  # 10 shares
        money = context.sell("AAPL", 999.0, 120.0, pd.Timestamp("2023-01-02"))
        # Should sell only 10 shares, not 999
        assert money == pytest.approx(10.0 * 120.0)
        assert context.get_position("AAPL") is None

    def test_sell_no_position(self, context):
        money = context.sell("AAPL", 5.0, 100.0, pd.Timestamp("2023-01-01"))
        assert money == 0.0

    def test_sell_logs_event(self, context, event_log):
        context.buy("AAPL", 1000.0, 100.0, pd.Timestamp("2023-01-01"))
        context.sell("AAPL", 5.0, 120.0, pd.Timestamp("2023-01-02"), reason="STOP")
        sell_events = [e for e in event_log if e["event_type"] == "STOP"]
        assert len(sell_events) == 1

    def test_sell_with_slippage(self):
        log = []
        ctx = Context(10000.0, 0.02, log)  # 2% slippage
        ctx.buy("AAPL", 1000.0, 100.0, pd.Timestamp("2023-01-01"))
        # Sell price = 120 * (1 - 0.02) = 117.6
        shares_to_sell = 5.0
        money = ctx.sell("AAPL", shares_to_sell, 120.0, pd.Timestamp("2023-01-02"))
        assert money == pytest.approx(5.0 * 117.6)

    def test_sell_with_broker_fee(self):
        log = []
        ctx = Context(10000.0, 0.0, log, broker_fee=0.01)  # 1% fee
        ctx.buy("AAPL", 1000.0, 100.0, pd.Timestamp("2023-01-01"))
        money = ctx.sell("AAPL", 5.0, 120.0, pd.Timestamp("2023-01-02"))
        gross = 5.0 * 120.0
        fee = gross * 0.01
        assert money == pytest.approx(gross - fee)


# =========================================================================
# Close
# =========================================================================

class TestClose:
    def test_close_sells_entire_position(self, context):
        context.buy("AAPL", 1000.0, 100.0, pd.Timestamp("2023-01-01"))
        money = context.close("AAPL", 120.0, pd.Timestamp("2023-01-02"))
        assert money == pytest.approx(10.0 * 120.0)
        assert context.get_position("AAPL") is None

    def test_close_no_position(self, context):
        money = context.close("AAPL", 100.0, pd.Timestamp("2023-01-01"))
        assert money == 0.0

    def test_close_with_custom_reason(self, context, event_log):
        context.buy("AAPL", 1000.0, 100.0, pd.Timestamp("2023-01-01"))
        context.close("AAPL", 120.0, pd.Timestamp("2023-01-02"), reason="LIQUIDATE")
        close_events = [e for e in event_log if e["event_type"] == "LIQUIDATE"]
        assert len(close_events) == 1


# =========================================================================
# Buy Protected (multiples of 10)
# =========================================================================

class TestBuyProtected:
    def test_buy_protected_valid(self, context):
        shares = context.buy_protected("AAPL", 10, 100.0, pd.Timestamp("2023-01-01"))
        assert shares == 10

    def test_buy_protected_20_shares(self, context):
        shares = context.buy_protected("AAPL", 20, 50.0, pd.Timestamp("2023-01-01"))
        assert shares == 20

    def test_buy_protected_less_than_10(self, context):
        shares = context.buy_protected("AAPL", 5, 100.0, pd.Timestamp("2023-01-01"))
        assert shares == 0.0

    def test_buy_protected_not_multiple_of_10(self, context):
        shares = context.buy_protected("AAPL", 15, 100.0, pd.Timestamp("2023-01-01"))
        assert shares == 0.0

    def test_buy_protected_insufficient_funds(self, context):
        # 100 shares @ 200 = 20000 > 10000
        shares = context.buy_protected("AAPL", 100, 200.0, pd.Timestamp("2023-01-01"))
        assert shares == 0.0


# =========================================================================
# Pending Orders (execution delay)
# =========================================================================

class TestPendingOrders:
    def test_buy_with_delay_queues_order(self, context_with_delay):
        ctx = context_with_delay
        t0 = pd.Timestamp("2023-01-01 10:00:00")
        shares = ctx.buy("AAPL", 1000.0, 100.0, t0)
        assert shares == 0.0  # Not executed yet
        assert len(ctx.pending_orders) == 1
        assert ctx.get_balance() == 10000.0

    def test_pending_order_executes_after_delay(self, context_with_delay):
        ctx = context_with_delay
        t0 = pd.Timestamp("2023-01-01 10:00:00")
        ctx.buy("AAPL", 1000.0, 100.0, t0)
        
        # Process at t0 + 61 seconds (> 60s delay)
        t1 = t0 + pd.Timedelta(seconds=61)
        ctx.process_pending_orders("AAPL", 105.0, t1)
        
        assert ctx.get_position("AAPL") is not None
        assert len(ctx.pending_orders) == 0

    def test_pending_order_not_executed_before_delay(self, context_with_delay):
        ctx = context_with_delay
        t0 = pd.Timestamp("2023-01-01 10:00:00")
        ctx.buy("AAPL", 1000.0, 100.0, t0)
        
        # Process at t0 + 30s (< 60s delay)
        t1 = t0 + pd.Timedelta(seconds=30)
        ctx.process_pending_orders("AAPL", 105.0, t1)
        
        assert ctx.get_position("AAPL") is None
        assert len(ctx.pending_orders) == 1

    def test_duplicate_buy_prevented(self, context_with_delay):
        ctx = context_with_delay
        t0 = pd.Timestamp("2023-01-01 10:00:00")
        ctx.buy("AAPL", 1000.0, 100.0, t0)
        ctx.buy("AAPL", 2000.0, 100.0, t0)  # duplicate
        assert len(ctx.pending_orders) == 1

    def test_sell_with_delay_queues_order(self, context_with_delay):
        ctx = context_with_delay
        t0 = pd.Timestamp("2023-01-01 10:00:00")
        # First need a position (use _execute_buy directly to bypass delay)
        ctx._execute_buy("AAPL", 1000.0, 100.0, t0)
        
        t1 = t0 + pd.Timedelta(seconds=5)
        money = ctx.sell("AAPL", 5.0, 120.0, t1, reason="STOP")
        assert money == 0.0
        assert len(ctx.pending_orders) == 1


# =========================================================================
# Get Positions
# =========================================================================

class TestGetPositions:
    def test_empty_initially(self, context):
        assert context.get_positions() == {}

    def test_after_buy(self, context):
        context.buy("AAPL", 1000.0, 100.0, pd.Timestamp("2023-01-01"))
        positions = context.get_positions()
        assert "AAPL" in positions
        assert isinstance(positions["AAPL"], Position)

    def test_get_position_returns_none_for_unknown(self, context):
        assert context.get_position("UNKNOWN") is None


# =========================================================================
# Event Log Shape
# =========================================================================

class TestEventLog:
    def test_event_log_fields(self, context, event_log):
        context.buy("AAPL", 1000.0, 100.0, pd.Timestamp("2023-01-01"))
        assert len(event_log) == 1
        entry = event_log[0]
        assert "timestamp" in entry
        assert "event_type" in entry
        assert "ticker" in entry
        assert "price" in entry
        assert "money_change" in entry
        assert "portfolio_balance" in entry

    def test_multiple_events_accumulate(self, context, event_log):
        context.buy("AAPL", 500.0, 50.0, pd.Timestamp("2023-01-01"))
        context.buy("GOOG", 500.0, 100.0, pd.Timestamp("2023-01-02"))
        context.sell("AAPL", 5.0, 60.0, pd.Timestamp("2023-01-03"))
        assert len(event_log) == 3


# =========================================================================
# Load Model
# =========================================================================

class TestLoadModel:
    def test_load_pickle_model(self, tmp_path):
        # Create a temp data dir with a pickle file
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        model_obj = {"type": "test_model", "weights": [1, 2, 3]}
        model_path = data_dir / "test_model.pkl"
        with open(model_path, "wb") as f:
            pickle.dump(model_obj, f)
        
        log = []
        ctx = Context(1000.0, 0.0, log)
        
        # Temporarily change working directory
        original_dir = os.getcwd()
        try:
            os.chdir(tmp_path)
            loaded = ctx.load_model("test_model")
            assert loaded == model_obj
        finally:
            os.chdir(original_dir)

    def test_load_model_not_found(self, tmp_path):
        log = []
        ctx = Context(1000.0, 0.0, log)
        
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        
        original_dir = os.getcwd()
        try:
            os.chdir(tmp_path)
            with pytest.raises(FileNotFoundError):
                ctx.load_model("nonexistent_model")
        finally:
            os.chdir(original_dir)
