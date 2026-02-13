import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch
from fastapi.testclient import TestClient
from core.api import app

@pytest.fixture
def client():
    return TestClient(app)

class TestRigorousEngine:
    @staticmethod
    def _mock_empty_datasource(start_time, end_time):
        return pd.DataFrame()

    @staticmethod
    def _mock_single_bar_datasource(start_time, end_time):
        return pd.DataFrame({
            "timestamp": [pd.to_datetime("2023-01-01")],
            "ticker": ["AAPL"],
            "open": [100.0],
            "high": [105.0],
            "low": [95.0],
            "price": [102.0],
            "volume": [1000]
        })

    def test_run_backtest_empty_data(self, client):
        with patch("core.api.duckdb_datasource", side_effect=self._mock_empty_datasource):
            payload = {
                "start_date": "2023-01-01",
                "end_date": "2023-01-02",
                "initial_balance": 10000.0,
                "code": "class Strategy:\n    def on_bar(self, ctx, bar): pass"
            }
            res = client.post("/run-backtest", json=payload)
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "success"
            assert data["metrics"] == {} # Should handle empty gracefully

    def test_run_backtest_zero_balance(self, client):
        with patch("core.api.duckdb_datasource", side_effect=self._mock_single_bar_datasource):
            payload = {
                "start_date": "2023-01-01",
                "end_date": "2023-01-02",
                "initial_balance": 0.0,
                "code": "class Strategy:\n    def on_bar(self, ctx, bar): pass"
            }
            res = client.post("/run-backtest", json=payload)
            assert res.status_code == 200
            assert res.json()["status"] == "success"

    # --- Strategy Compilation Rigorous ---
    def test_strategy_compilation_missing_class(self, client):
        payload = {
            "start_date": "2023-01-01",
            "end_date": "2023-01-02",
            "code": "x = 10\nprint(x)" # No class defined
        }
        res = client.post("/run-backtest", json=payload)
        assert res.status_code == 400
        assert "No strategy class found" in res.json()["detail"]

    def test_strategy_compilation_multiple_classes(self, client):
        # Should pick the first one or 'Strategy'
        code = """
class Other: pass
class Strategy:
    def on_bar(self, ctx, bar): pass
"""
        with patch("core.api.duckdb_datasource", side_effect=self._mock_single_bar_datasource):
            payload = {
                "start_date": "2023-01-01",
                "end_date": "2023-01-02",
                "code": code
            }
            res = client.post("/run-backtest", json=payload)
            assert res.status_code == 200
            assert res.json()["status"] == "success"

    def test_strategy_compilation_syntax_error(self, client):
        payload = {
            "start_date": "2023-01-01",
            "end_date": "2023-01-02",
            "code": "def improper_syntax("
        }
        res = client.post("/run-backtest", json=payload)
        assert res.status_code == 400
        assert "Error compiling strategy" in res.json()["detail"]

    def test_strategy_runtime_error(self, client):
        # Compilation succeeds, but execution fails during engine.run()
        code = """
class Strategy:
    def on_bar(self, ctx, bar):
        raise ValueError("Runtime explosion")
"""
        with patch("core.api.duckdb_datasource", side_effect=self._mock_single_bar_datasource):
            payload = {
                "start_date": "2023-01-01",
                "end_date": "2023-01-02",
                "code": code
            }
            res = client.post("/run-backtest", json=payload)
            assert res.status_code == 500
            assert "Runtime explosion" in res.json()["detail"]
