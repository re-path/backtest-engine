import pytest
import os
import subprocess
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from core.api import app

@pytest.fixture
def client():
    return TestClient(app)

class TestRigorousLiveWorkflow:
    @patch("subprocess.run")
    @patch("redis.Redis")
    @patch("os.path.exists")
    def test_live_simultaneous_starts(self, mock_exists, mock_redis_cls, mock_run, client):
        """Simulate starting multiple strategies in quick succession."""
        mock_exists.return_value = True
        mock_redis = MagicMock()
        mock_redis_cls.return_value = mock_redis
        
        # Mock status sequence for 2 strats
        mock_redis.get.side_effect = ["stopped", "running", "stopped", "running"]
        
        res1 = client.post("/live/strategies/start", json={"strategy_name": "strat1"})
        res2 = client.post("/live/strategies/start", json={"strategy_name": "strat2"})
        
        assert res1.status_code == 200
        assert res2.status_code == 200
        assert mock_run.call_count == 2

    @patch("subprocess.run")
    @patch("redis.Redis")
    def test_live_stop_status_update(self, mock_redis_cls, mock_run, client):
        """Verify that the stop endpoint directly sets Redis status to 'stopped'."""
        mock_redis = MagicMock()
        mock_redis_cls.return_value = mock_redis
        
        res = client.post("/live/strategies/stop", json={"strategy_name": "test_strat"})
        assert res.status_code == 200
        
        # Check if Redis mock was called with 'stopped'
        # calls: set(stopping), set(stopped)
        mock_redis.set.assert_any_call("strategy:test_strat:status", "stopping")
        mock_redis.set.assert_any_call("strategy:test_strat:status", "stopped")

    @patch("subprocess.run")
    @patch("redis.Redis")
    def test_live_start_failure_exception(self, mock_redis_cls, mock_run, client):
        """Verify 500 on subprocess error."""
        with patch("os.path.exists", return_value=True):
            mock_run.side_effect = subprocess.CalledProcessError(1, "ksai_proc")
            res = client.post("/live/strategies/start", json={"strategy_name": "fail_strat"})
            assert res.status_code == 500
            assert "Failed to launch process" in res.json()["detail"]

    @patch("subprocess.run")
    @patch("redis.Redis")
    @patch("os.path.exists")
    def test_live_start_timeout_waiting_for_redis(self, mock_exists, mock_redis_cls, mock_run, client):
        """
        Verify that if Redis status never becomes 'running', we return a warning.
        """
        mock_exists.return_value = True
        mock_redis = MagicMock()
        mock_redis_cls.return_value = mock_redis
        
        # Redis always returns 'stopped' or None
        mock_redis.get.return_value = "stopped"
        
        # Patch sleep to make test fast
        with patch("time.sleep", return_value=None):
            res = client.post("/live/strategies/start", json={"strategy_name": "slow_strat"})
            assert res.status_code == 200
            assert res.json()["status"] == "warning"
            assert "not yet 'running'" in res.json()["message"]
