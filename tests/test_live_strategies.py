import pytest
import os
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from core.api import app

@pytest.fixture
def client():
    return TestClient(app)

class TestLiveStrategies:
    @patch("redis.Redis")
    def test_list_live_strategies(self, mock_redis_cls, client, tmp_path):
        # Mock Redis
        mock_redis = MagicMock()
        mock_redis_cls.return_value = mock_redis
        mock_redis.get.return_value = "running"
        
        # Mock STRATEGIES_DIR
        import core.api as api_module
        orig_dir = api_module.STRATEGIES_DIR
        test_dir = str(tmp_path / "strategies")
        os.makedirs(test_dir, exist_ok=True)
        with open(os.path.join(test_dir, "test_strat.py"), "w") as f:
            f.write("class Strategy: pass")
            
        api_module.STRATEGIES_DIR = test_dir
        
        try:
            res = client.get("/live/strategies")
            assert res.status_code == 200
            data = res.json()
            assert len(data) == 1
            assert data[0]["name"] == "test_strat"
            assert data[0]["status"] == "running"
        finally:
            api_module.STRATEGIES_DIR = orig_dir

    @patch("subprocess.run")
    @patch("redis.Redis")
    @patch("os.path.exists")
    def test_start_live_strategy(self, mock_exists, mock_redis_cls, mock_run, client):
        mock_exists.return_value = True
        mock_redis = MagicMock()
        mock_redis_cls.return_value = mock_redis
        
        # Mock status sequence: first 'stopped' then 'running'
        mock_redis.get.side_effect = ["stopped", "running", "running"]
        
        payload = {"strategy_name": "my_strat"}
        res = client.post("/live/strategies/start", json=payload)
        
        assert res.status_code == 200
        assert res.json()["status"] == "success"
        
        # Verify ksai_proc was called
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "ksai_proc" in args
        assert "--name" in args
        assert "my_strat" in args

    @patch("subprocess.run")
    @patch("redis.Redis")
    def test_stop_live_strategy(self, mock_redis_cls, mock_run, client):
        mock_redis = MagicMock()
        mock_redis_cls.return_value = mock_redis
        
        payload = {"strategy_name": "my_strat"}
        res = client.post("/live/strategies/stop", json=payload)
        
        assert res.status_code == 200
        assert res.json()["status"] == "success"
        
        # Verify redis status update
        mock_redis.set.assert_called_with("strategy:my_strat:status", "stopped")
        
        # Verify ksai_proc stop was called
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "ksai_proc" in args
        assert "stop" in args
        assert "my_strat" in args
