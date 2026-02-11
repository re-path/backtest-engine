"""
Integration tests for FastAPI endpoints using TestClient.
No live server needed.
"""
import pytest
import os
import json
import shutil
import tempfile
from unittest.mock import patch, MagicMock
import pandas as pd

from fastapi.testclient import TestClient
from core.api import app, STRATEGIES_DIR, NOTEBOOKS_DIR, SQL_SNIPPETS_DIR


@pytest.fixture
def client():
    """FastAPI TestClient."""
    return TestClient(app)


# We back up / restore directories to avoid polluting real resources
@pytest.fixture(autouse=True)
def isolate_resource_dirs(tmp_path):
    """
    For tests that create files, we temporarily override the global dirs
    so we don't pollute the real resources/ directory.
    """
    import core.api as api_module
    
    orig_strat = api_module.STRATEGIES_DIR
    orig_note = api_module.NOTEBOOKS_DIR
    orig_sql = api_module.SQL_SNIPPETS_DIR
    
    test_strat = str(tmp_path / "strategies")
    test_note = str(tmp_path / "notebooks")
    test_sql = str(tmp_path / "sql_snippets")
    
    os.makedirs(test_strat, exist_ok=True)
    os.makedirs(test_note, exist_ok=True)
    os.makedirs(test_sql, exist_ok=True)
    os.makedirs(os.path.join(test_sql, "General"), exist_ok=True)
    
    api_module.STRATEGIES_DIR = test_strat
    api_module.NOTEBOOKS_DIR = test_note
    api_module.SQL_SNIPPETS_DIR = test_sql
    
    yield
    
    api_module.STRATEGIES_DIR = orig_strat
    api_module.NOTEBOOKS_DIR = orig_note
    api_module.SQL_SNIPPETS_DIR = orig_sql


# =========================================================================
# Strategies CRUD
# =========================================================================

class TestStrategies:
    def test_list_strategies_empty(self, client):
        res = client.get("/strategies")
        assert res.status_code == 200
        assert res.json() == []

    def test_save_strategy(self, client):
        payload = {"name": "my_strat", "code": "class Strategy:\n  pass", "params": {}}
        res = client.post("/strategies", json=payload)
        assert res.status_code == 200
        assert res.json()["status"] == "success"

    def test_list_strategies_after_save(self, client):
        payload = {"name": "alpha", "code": "x = 1", "params": {}}
        client.post("/strategies", json=payload)
        res = client.get("/strategies")
        assert res.status_code == 200
        strategies = res.json()
        assert len(strategies) == 1
        assert strategies[0]["name"] == "alpha"

    def test_get_strategy_by_name(self, client):
        payload = {"name": "beta", "code": "y = 2", "params": {}}
        client.post("/strategies", json=payload)
        res = client.get("/strategies/beta")
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "beta"
        assert data["code"] == "y = 2"

    def test_get_strategy_not_found(self, client):
        res = client.get("/strategies/nonexistent")
        assert res.status_code == 404

    def test_save_strategy_invalid_name(self, client):
        payload = {"name": "!!!???", "code": "x = 1", "params": {}}
        res = client.post("/strategies", json=payload)
        assert res.status_code == 400

    def test_save_strategy_overwrites(self, client):
        payload1 = {"name": "gamma", "code": "v1", "params": {}}
        payload2 = {"name": "gamma", "code": "v2", "params": {}}
        client.post("/strategies", json=payload1)
        client.post("/strategies", json=payload2)
        res = client.get("/strategies/gamma")
        assert res.json()["code"] == "v2"


# =========================================================================
# Notebooks
# =========================================================================

class TestNotebooks:
    def test_list_notebooks_empty(self, client):
        res = client.get("/notebooks")
        assert res.status_code == 200
        assert res.json() == []

    def test_create_notebook(self, client):
        payload = {"name": "test_nb"}
        res = client.post("/notebooks", json=payload)
        assert res.status_code == 200
        assert res.json()["status"] == "success"

    def test_create_duplicate_notebook(self, client):
        payload = {"name": "dup_nb"}
        client.post("/notebooks", json=payload)
        res = client.post("/notebooks", json=payload)
        assert res.status_code == 400

    def test_create_notebook_invalid_name(self, client):
        payload = {"name": "!!!"}
        res = client.post("/notebooks", json=payload)
        assert res.status_code == 400

    def test_list_notebooks_after_create(self, client):
        client.post("/notebooks", json={"name": "nb1"})
        res = client.get("/notebooks")
        notebooks = res.json()
        assert len(notebooks) == 1
        assert notebooks[0]["name"] == "nb1"


# =========================================================================
# Backtest
# =========================================================================

class TestBacktest:
    @staticmethod
    def _mock_datasource(start_time, end_time):
        return pd.DataFrame({
            "timestamp": pd.date_range("2023-01-01", periods=5, freq="D"),
            "ticker": ["AAPL"] * 5,
            "price": [100.0, 102.0, 101.0, 103.0, 105.0],
        })

    def test_run_backtest_with_default_strategy(self, client):
        """Run backtest with explicit strategy code."""
        with patch("core.api.duckdb_datasource", side_effect=self._mock_datasource):
            code = """
class Strategy:
    def __init__(self, **kwargs): pass
    def on_bar(self, context, bar): pass
"""
            payload = {
                "start_date": "2023-01-01",
                "end_date": "2023-01-06",
                "initial_balance": 10000.0,
                "slippage": 0.0,
                "code": code
            }
            res = client.post("/run-backtest", json=payload)
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "success"

    def test_run_backtest_with_custom_code(self, client):
        code = """
class Strategy:
    def __init__(self, **kwargs):
        pass
    def on_bar(self, context, bar):
        pass
"""
        with patch("core.api.duckdb_datasource", side_effect=self._mock_datasource):
            payload = {
                "start_date": "2023-01-01",
                "end_date": "2023-01-04",
                "initial_balance": 10000.0,
                "code": code,
            }
            res = client.post("/run-backtest", json=payload)
            assert res.status_code == 200

    def test_run_backtest_bad_code(self, client):
        with patch("core.api.duckdb_datasource", side_effect=self._mock_datasource):
            payload = {
                "start_date": "2023-01-01",
                "end_date": "2023-01-03",
                "code": "this is not valid python!!!"
            }
            res = client.post("/run-backtest", json=payload)
            # May return 400 (compile error) or 500 depending on exec path
            assert res.status_code in (400, 500)


# =========================================================================
# Last Log
# =========================================================================

class TestLastLog:
    def test_get_last_log_empty(self, client):
        import core.api as api_module
        api_module.last_backtest_results["event_log"] = None
        res = client.get("/backtest/last-log")
        assert res.status_code == 200
        assert res.json()["event_log"] == []


# =========================================================================
# ML Models
# =========================================================================

class TestMLModels:
    def test_list_models_no_data_dir(self, client):
        with patch("os.path.exists", return_value=False):
            res = client.get("/models")
            assert res.status_code == 200
            assert res.json() == []

    def test_train_model_simple(self, client, tmp_path):
        code = """
import pickle
result = {"accuracy": 0.95}
save_model(result)
"""
        with patch("core.api.duckdb_datasource") as mock_ds:
            mock_ds.return_value = pd.DataFrame()
            payload = {
                "name": "test_model",
                "code": code,
            }
            res = client.post("/train", json=payload)
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "success"

    def test_train_model_error(self, client):
        code = "raise ValueError('intentional error')"
        payload = {
            "name": "bad_model",
            "code": code,
        }
        res = client.post("/train", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "error"
        assert "intentional error" in data["error"]


# =========================================================================
# SQL Snippets
# =========================================================================

class TestSQLSnippets:
    def test_list_snippets_empty(self, client):
        res = client.get("/sql-snippets")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, dict)

    def test_save_snippet(self, client):
        payload = {
            "name": "all_trades",
            "category": "General",
            "code": "SELECT * FROM trades;",
        }
        res = client.post("/sql-snippets", json=payload)
        assert res.status_code == 200
        assert res.json()["status"] == "success"

    def test_save_and_list_snippet(self, client):
        client.post("/sql-snippets", json={
            "name": "top10",
            "category": "Analysis",
            "code": "SELECT * FROM trades LIMIT 10;",
        })
        res = client.get("/sql-snippets")
        data = res.json()
        assert "Analysis" in data
        assert len(data["Analysis"]) == 1
        assert data["Analysis"][0]["name"] == "top10"

    def test_save_snippet_invalid_name(self, client):
        payload = {"name": "!!!", "category": "General", "code": "SELECT 1;"}
        res = client.post("/sql-snippets", json=payload)
        assert res.status_code == 400

    def test_snippet_default_category(self, client):
        payload = {"name": "simple", "code": "SELECT 1;"}
        res = client.post("/sql-snippets", json=payload)
        assert res.status_code == 200


# =========================================================================
# Optimization endpoint
# =========================================================================

class TestOptimization:
    @staticmethod
    def _mock_ds(start_time, end_time):
        return pd.DataFrame({
            "timestamp": pd.date_range("2023-01-01", periods=5, freq="D"),
            "ticker": ["AAPL"] * 5,
            "price": [100.0, 102.0, 101.0, 103.0, 105.0],
        })

    def test_optimization_endpoint(self, client):
        code = """
class Strategy:
    def __init__(self, threshold=0.5, **kwargs):
        self.threshold = threshold
    def on_bar(self, context, bar):
        pass
"""
        with patch("core.api.duckdb_datasource", side_effect=self._mock_ds):
            payload = {
                "code": code,
                "ranges": {
                    "threshold": {"min": 0.1, "max": 1.0, "step": 0.1}
                },
                "algorithm": "hill_climb",
                "target_metric": "total_net_profit",
                "start_date": "2023-01-01",
                "end_date": "2023-01-06",
                "initial_balance": 10000.0,
            }
            res = client.post("/optimize", json=payload)
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "success"
            assert "results" in data


# =========================================================================
# Root redirect
# =========================================================================

class TestRoot:
    def test_root_not_on_api_app(self, client):
        """The root '/' redirect is registered in main.py, not api.py.
        So the api-only TestClient should 404 here."""
        res = client.get("/", follow_redirects=False)
        # It's registered in main.py, not api.py — just confirm no crash
        assert res.status_code in (307, 404)
