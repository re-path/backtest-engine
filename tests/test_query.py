import pytest
from core.datasources import query

def test_show_databases():
    """Test that 'raw' and 'ohlcv' databases are attached and visible."""
    df = query("SHOW DATABASES")
    
    # query returns a Polars DataFrame
    databases = df.get_column("database_name").to_list()
    
    assert 'raw' in databases, "'raw' database not found in SHOW DATABASES"
    assert 'ohlcv' in databases, "'ohlcv' database not found in SHOW DATABASES"

def test_query_views_exist():
    """Test that the created views can be queried successfully."""
    try:
        raw_df = query("SELECT * FROM raw.floorsheet LIMIT 1")
        ohlcv_1d_df = query("SELECT * FROM ohlcv.ohlcv_1d LIMIT 1")
        ohlcv_1w_df = query("SELECT * FROM ohlcv.ohlcv_1w LIMIT 1")
        ohlcv_1m_df = query("SELECT * FROM ohlcv.ohlcv_1m LIMIT 1")
        
        # If execution reaches here, the views exist and syntax is valid.
        assert True
    except Exception as e:
        pytest.fail(f"Querying views raised an exception: {e}")
