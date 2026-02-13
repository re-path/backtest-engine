import pytest
import os
import shutil
import tempfile
from fastapi.testclient import TestClient
from core.api import app, STRATEGIES_DIR, NOTEBOOKS_DIR, SQL_SNIPPETS_DIR

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture(autouse=True)
def isolate_resources(tmp_path):
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

class TestRigorousAPI:
    # --- SQL Snippets Rigorous ---
    def test_sql_snippets_special_characters(self, client):
        payload = {
            "name": "complex-query_v1",
            "category": "High-Importance/Reports",
            "code": "SELECT * FROM trades WHERE symbol = 'AAPL' AND price > 100 -- comment with emoji 🚀;"
        }
        res = client.post("/sql-snippets", json=payload)
        assert res.status_code == 200
        
        # Verify it saved and can be listed
        res = client.get("/sql-snippets")
        data = res.json()
        # The category might be sanitized
        safe_cat = "HighImportanceReports" # Based on logic: "".join([c for c in snippet.category if c.isalpha() or c.isdigit() or c in (' ', '_', '-')]).strip()
        # Wait, the logic is: safe_cat = "".join([c for c in snippet.category if c.isalpha() or c.isdigit() or c in (' ', '_', '-')]).strip() or "General"
        # "High-Importance/Reports" -> "High-ImportanceReports"
        found = False
        for cat, list_ in data.items():
            for s in list_:
                if s["name"] == "complex-query_v1":
                    assert "🚀" in s["code"]
                    found = True
        assert found

    def test_sql_snippets_empty_code(self, client):
        payload = {"name": "empty", "category": "General", "code": ""}
        res = client.post("/sql-snippets", json=payload)
        # Should succeed as per current impl (it just writes the file)
        assert res.status_code == 200

    def test_sql_snippets_invalid_name(self, client):
        payload = {"name": "../../../etc/passwd", "category": "General", "code": "SELECT 1;"}
        res = client.post("/sql-snippets", json=payload)
        # Sanitization logic: "".join([c for c in snippet.name if c.isalpha() or c.isdigit() or c in (' ', '_', '-')]).strip()
        # "../../../etc/passwd" -> "etcpasswd"
        assert res.status_code == 200
        res = client.get("/sql-snippets")
        assert "etcpasswd" in [s["name"] for s in res.json().get("General", [])]

    # --- Strategies Rigorous ---
    def test_strategies_very_large_code(self, client):
        large_code = "class Strategy:\n" + "    pass\n" * 10000
        payload = {"name": "large_strat", "code": large_code, "params": {}}
        res = client.post("/strategies", json=payload)
        assert res.status_code == 200
        
        res = client.get("/strategies/large_strat")
        assert len(res.json()["code"]) == len(large_code)

    def test_strategies_get_nonexistent(self, client):
        res = client.get("/strategies/does_not_exist")
        assert res.status_code == 404

    # --- Live Strategies Rigorous ---
    def test_live_strategies_start_missing_file(self, client):
        res = client.post("/live/strategies/start", json={"strategy_name": "missing_physical_file"})
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

    def test_live_strategies_list_integrity(self, client):
        # Ensure that non-py files are ignored (if any)
        with open(os.path.join(STRATEGIES_DIR, "not_a_strategy.txt"), "w") as f:
            f.write("test")
        res = client.get("/live/strategies")
        assert "not_a_strategy" not in [s["name"] for s in res.json()]
