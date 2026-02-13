import pytest
import os
import time
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from core.api import app

@pytest.fixture
def client():
    return TestClient(app)

class TestAPIWorkflow:
    @patch("subprocess.run")
    @patch("redis.Redis")
    def test_full_live_lifecycle(self, mock_redis_cls, mock_run, client, tmp_path):
        """
        Verify: Save Strategy -> List -> Start -> Monitor -> Stop
        """
        mock_redis = MagicMock()
        mock_redis_cls.return_value = mock_redis
        
        # 1. Save Strategy
        strat_name = "workflow_test_strat"
        save_res = client.post("/strategies", json={
            "name": strat_name,
            "code": "class Strategy: pass",
            "params": {}
        })
        assert save_res.status_code == 200
        
        # 2. List Live Strategies (should be stopped initially)
        mock_redis.get.return_value = "stopped"
        list_res = client.get("/live/strategies")
        assert list_res.status_code == 200
        strats = list_res.json()
        target = next(s for s in strats if s["name"] == strat_name)
        assert target["status"] == "stopped"
        
        # 3. Start Strategy
        # Mock Redis status transition
        mock_redis.get.side_effect = ["stopped", "running", "running"]
        start_res = client.post("/live/strategies/start", json={"strategy_name": strat_name})
        assert start_res.status_code == 200
        assert start_res.json()["status"] == "success"
        
        # 4. Stop Strategy
        stop_res = client.post("/live/strategies/stop", json={"strategy_name": strat_name})
        assert stop_res.status_code == 200
        assert stop_res.json()["status"] == "success"
        
        # Verify Redis was updated to 'stopped'
        mock_redis.set.assert_called_with(f"strategy:{strat_name}:status", "stopped")
