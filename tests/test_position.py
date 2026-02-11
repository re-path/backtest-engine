"""
Unit tests for the Position class.
"""
import pytest
import pandas as pd
from core.context import Position


class TestPosition:
    def test_construction(self):
        pos = Position("AAPL", 10.0, 150.0, pd.Timestamp("2023-01-01"))
        assert pos.ticker == "AAPL"
        assert pos.share_units == 10.0
        assert pos.entry_price == 150.0
        assert pos.time == pd.Timestamp("2023-01-01")

    def test_share_units_mutable(self):
        pos = Position("GOOG", 100.0, 200.0, "2023-06-15")
        pos.share_units += 50.0
        assert pos.share_units == 150.0
        pos.share_units -= 30.0
        assert pos.share_units == 120.0

    def test_zero_shares(self):
        pos = Position("MSFT", 0.0, 300.0, None)
        assert pos.share_units == 0.0

    def test_time_can_be_any_type(self):
        # Engine uses various time representations
        pos1 = Position("X", 1.0, 1.0, "2023-01-01")
        pos2 = Position("X", 1.0, 1.0, 1672531200)
        pos3 = Position("X", 1.0, 1.0, None)
        assert pos1.time == "2023-01-01"
        assert pos2.time == 1672531200
        assert pos3.time is None
