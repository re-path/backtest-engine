"""
Tests for DuckDBManager and data source classes.

Unit tests that don't require real data use mocking.
Integration tests that hit real DuckDB files are marked with @pytest.mark.integration.
"""
import pytest
import os
import pandas as pd
from unittest.mock import patch, MagicMock, PropertyMock

from core.datasources.duckdb_manager import DuckDBManager
from core.datasources.sources import (
    BaseDuckDBSource,
    FloorsheetSource,
    OHLCVSource,
    DailyCloseSource,
    DailyOHLCSource,
    ContextualFloorsheetSource,
)


# =========================================================================
# DuckDBManager
# =========================================================================

class TestDuckDBManager:
    def test_singleton(self):
        """get_instance returns the same object."""
        # Reset singleton for clean testing
        old = DuckDBManager._instance
        try:
            DuckDBManager._instance = None
            m1 = DuckDBManager.get_instance()
            m2 = DuckDBManager.get_instance()
            assert m1 is m2
        finally:
            DuckDBManager._instance = old

    def test_missing_env_var(self):
        """Raises if DATASOURCE_FOLDER not set."""
        old = DuckDBManager._instance
        old_con = DuckDBManager._con
        try:
            DuckDBManager._instance = None
            DuckDBManager._con = None
            with patch.dict(os.environ, {}, clear=True):
                # Remove the var entirely
                env_backup = os.environ.pop("DATASOURCE_FOLDER", None)
                try:
                    with pytest.raises(ValueError, match="DATASOURCE_FOLDER"):
                        DuckDBManager()
                finally:
                    if env_backup is not None:
                        os.environ["DATASOURCE_FOLDER"] = env_backup
        finally:
            DuckDBManager._instance = old
            DuckDBManager._con = old_con

    def test_get_base_path_ends_with_floorsheets(self):
        """If DATASOURCE_FOLDER already ends with floorsheets, no duplication."""
        manager = DuckDBManager.get_instance()
        base = manager.get_base_path()
        assert base.endswith("floorsheets")
        assert not base.endswith("floorsheets/floorsheets")

    def test_execute(self):
        """Basic execute works."""
        manager = DuckDBManager.get_instance()
        result = manager.execute("SELECT 1 AS val")
        df = result.df()
        assert df.iloc[0]["val"] == 1


# =========================================================================
# BaseDuckDBSource._get_target_globs
# =========================================================================

class TestGetTargetGlobs:
    def test_single_day(self):
        source = BaseDuckDBSource()
        start = pd.Timestamp("2023-06-27")
        end = pd.Timestamp("2023-06-28")
        globs = source._get_target_globs(start, end)
        # Should contain globs for at least 2023-06-27 (if data exists)
        # Result depends on whether actual files exist on disk
        assert isinstance(globs, list)

    def test_empty_range(self):
        source = BaseDuckDBSource()
        start = pd.Timestamp("2023-06-27 23:59:59")
        end = pd.Timestamp("2023-06-27 23:59:59")
        globs = source._get_target_globs(start, end)
        # Should handle gracefully (may return 1 or 0 depending on floor/ceil)
        assert isinstance(globs, list)

    def test_multi_day_range(self):
        source = BaseDuckDBSource()
        start = pd.Timestamp("2023-06-27")
        end = pd.Timestamp("2023-06-30")
        globs = source._get_target_globs(start, end)
        assert isinstance(globs, list)


# =========================================================================
# Source classes: empty result handling
# =========================================================================

class TestSourcesEmptyResult:
    """All sources should return an empty DataFrame when no data files match."""

    def test_floorsheet_no_data(self):
        source = FloorsheetSource()
        df = source.query("2000-01-01", "2000-01-02")
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_ohlcv_no_data(self):
        source = OHLCVSource()
        df = source.query("2000-01-01", "2000-01-02")
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_daily_close_no_data(self):
        source = DailyCloseSource()
        df = source.query("2000-01-01", "2000-01-02")
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_daily_ohlc_no_data(self):
        source = DailyOHLCSource()
        df = source.query("2000-01-01", "2000-01-02")
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_contextual_no_data(self):
        source = ContextualFloorsheetSource(lookback_period="1 DAY")
        df = source.query("2000-01-01", "2000-01-02")
        assert isinstance(df, pd.DataFrame)
        assert df.empty


# =========================================================================
# Integration tests (need real data files on disk)
# =========================================================================

@pytest.mark.integration
class TestFloorsheetSourceIntegration:
    def test_query_returns_data(self):
        source = FloorsheetSource()
        df = source.query("2023-06-27", "2023-06-28")
        assert not df.empty
        assert "timestamp" in df.columns
        assert "ticker" in df.columns
        assert "price" in df.columns
        assert "contract_id" in df.columns

    def test_query_columns(self):
        source = FloorsheetSource()
        df = source.query("2023-06-27", "2023-06-28")
        if not df.empty:
            assert "buyer_broker" in df.columns


@pytest.mark.integration
class TestOHLCVSourceIntegration:
    def test_query_returns_ohlcv(self):
        source = OHLCVSource()
        df = source.query("2023-06-27", "2023-06-28")
        assert not df.empty
        for col in ["timestamp", "ticker", "open", "high", "low", "close", "volume"]:
            assert col in df.columns


@pytest.mark.integration
class TestDailyCloseSourceIntegration:
    def test_query_returns_daily_close(self):
        source = DailyCloseSource()
        df = source.query("2023-06-27", "2023-06-28")
        assert not df.empty
        assert "timestamp" in df.columns
        assert "ticker" in df.columns
        assert "price" in df.columns


@pytest.mark.integration
class TestDailyOHLCSourceIntegration:
    def test_query_returns_daily_ohlc(self):
        source = DailyOHLCSource()
        df = source.query("2023-06-27", "2023-06-28")
        assert not df.empty
        for col in ["timestamp", "ticker", "open", "high", "low", "close", "volume"]:
            assert col in df.columns


@pytest.mark.integration
class TestContextualFloorsheetSourceIntegration:
    def test_query_has_prev_stats(self):
        source = ContextualFloorsheetSource(lookback_period="1 DAY")
        df = source.query("2025-03-12", "2025-03-13")
        if df.empty:
            pytest.skip("No data for 2025-03-12/13")
        for col in ["prev_open", "prev_high", "prev_low", "prev_close", "prev_volume"]:
            assert col in df.columns
