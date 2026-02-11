# core/api.py

import pandas as pd
import numpy as np
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import os
import glob
import io
from contextlib import redirect_stdout

from core.engine import BacktestEngineWithSource, plot_simulation_trades, filesystem_datasource, duckdb_datasource
from core.analysis import analyze_portfolio
from core.context import Context 
from core.datasources.sources import DailyOHLCSource 

app = FastAPI()

# Global storage for the last backtest run
last_backtest_results = {
    "event_log": None
}

class StrategyModel(BaseModel):
    name: str
    code: str
    params: Dict[str, Any]
    date: Optional[str] = None


STRATEGIES_DIR = "resources/strategies"
os.makedirs(STRATEGIES_DIR, exist_ok=True)

@app.get("/strategies")
async def list_strategies():
    strategies = []
    files = glob.glob(os.path.join(STRATEGIES_DIR, "*.py"))
    for f in files:
        try:
            # For now, just listing the filename without parsing content for metadata
            name = os.path.basename(f).replace(".py", "")
            strategies.append({
                "name": name,
                "date": datetime.fromtimestamp(os.path.getmtime(f)).isoformat(),
            })
        except Exception:
            continue
    return sorted(strategies, key=lambda x: x['date'], reverse=True)

@app.get("/strategies/{name}")
async def get_strategy(name: str):
    file_path = os.path.join(STRATEGIES_DIR, f"{name}.py")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    try:
        with open(file_path, 'r') as file:
            code = file.read()
            # Return empty params as we are not persisting them in the file yet
            # The client should handle this gracefully (e.g. keep existing params or default)
            return {
                "name": name,
                "code": code,
                "params": {} 
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/strategies")
async def save_strategy(strategy: StrategyModel):
    # Sanitize name
    safe_name = "".join([c for c in strategy.name if c.isalpha() or c.isdigit() or c in (' ', '_', '-')]).rstrip()
    if not safe_name:
        raise HTTPException(status_code=400, detail="Invalid strategy name")
        
    file_path = os.path.join(STRATEGIES_DIR, f"{safe_name}.py")
    
    try:
        with open(file_path, 'w') as file:
            file.write(strategy.code)
        return {"status": "success", "message": f"Saved {safe_name}"}
    except Exception as e:
        # traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))





NOTEBOOKS_DIR = "resources/notebooks"
os.makedirs(NOTEBOOKS_DIR, exist_ok=True)

class NotebookModel(BaseModel):
    name: str

@app.get("/notebooks")
async def list_notebooks():
    notebooks = []
    files = glob.glob(os.path.join(NOTEBOOKS_DIR, "*.py"))
    for f in files:
        try:
            name = os.path.basename(f).replace(".py", "")
            notebooks.append({
                "name": name,
                "date": datetime.fromtimestamp(os.path.getmtime(f)).isoformat(),
            })
        except Exception:
            continue
    return sorted(notebooks, key=lambda x: x['date'], reverse=True)

@app.post("/notebooks")
async def create_notebook(notebook: NotebookModel):
    safe_name = "".join([c for c in notebook.name if c.isalpha() or c.isdigit() or c in (' ', '_', '-')]).rstrip()
    if not safe_name:
        raise HTTPException(status_code=400, detail="Invalid notebook name")
        
    file_path = os.path.join(NOTEBOOKS_DIR, f"{safe_name}.py")
    
    if os.path.exists(file_path):
        raise HTTPException(status_code=400, detail="Notebook already exists")
    
    # Minimal Marimo Template
    template = '''import marimo

__generated_with = "0.10.9"
app = marimo.App(width="full")

@app.cell
def _():
    import marimo as mo
    return (mo,)

if __name__ == "__main__":
    app.run()
'''
    try:
        with open(file_path, 'w') as file:
            file.write(template)
        return {"status": "success", "message": f"Created {safe_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class BacktestRequest(BaseModel):
    start_date: str  
    end_date: str    
    initial_balance: float = 10000.0
    slippage: float = 0.01
    broker_fee: float = 0.0
    annual_interest_rate: float = 0.0
    strategy_params: Dict[str, Any] = {}
    code: Optional[str] = None

class SimpleTestStrategy:
    def __init__(self, **kwargs):
        self.params = kwargs

    def on_bar(self, context, bar):
        last_price = context.get_state('last_price', 0)
        
        if last_price == 0:
            context.set_state('last_price', bar.price)
            return

        if bar.price > last_price:
            invest_amount = context.get_balance() * 0.10 # Invest 10%
            context.buy(bar.ticker, invest_amount, bar.price, bar.timestamp)
        elif bar.price < last_price:
            context.close(bar.ticker, bar.price, bar.timestamp, "TrendRev")
        
        context.set_state('last_price', bar.price)

@app.post("/run-backtest")
async def run_backtest_endpoint(request: BacktestRequest):
    try:
        start_dt = pd.to_datetime(request.start_date)
        end_dt = pd.to_datetime(request.end_date) # Fixed: was requesting request.end_date twice in original potentially or just logic flow

        strategy_cls = SimpleTestStrategy
        
        # Dynamic Strategy Execution
        if request.code:
            try:
                # Define a local scope for execution
                local_scope = {}
                # Execute the code
                exec(request.code, globals(), local_scope)
                
                # Look for a class named 'Strategy' inside the executed code
                if 'Strategy' in local_scope:
                    strategy_cls = local_scope['Strategy']
                else:
                    # Fallback: try to find the first class defined
                    import inspect
                    classes = [obj for name, obj in local_scope.items() if inspect.isclass(obj)]
                    if classes:
                        strategy_cls = classes[0]
                    else:
                        raise ValueError("No strategy class found in the provided code. Please name your class 'Strategy'.")
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Error compiling strategy: {str(e)}")

        engine = BacktestEngineWithSource(
            data_source_func=duckdb_datasource,
            start_time=start_dt,
            end_time=end_dt,
            interval=pd.Timedelta(days=1), 
            strategy_cls=strategy_cls, 
            initial_money=request.initial_balance,
            slippage=request.slippage,
            broker_fee=request.broker_fee,
            annual_interest_rate=request.annual_interest_rate,
            execution_delay=0,
            strategy_params=request.strategy_params
        )

        print(">>> Starting Engine execution...")
        event_log_df = engine.run()
        print(f">>> Engine finished. Log size: {len(event_log_df)} rows")

        # Save for later retrieval by detail tabs
        last_backtest_results["event_log"] = event_log_df

        metrics_df = analyze_portfolio(event_log_df)
        
        fig = plot_simulation_trades(event_log_df)
        plot_html = fig.to_html(full_html=False, include_plotlyjs=True)

        metrics_dict = metrics_df.to_dict(orient='records')[0] if metrics_df is not None else {}
        
        event_log_dict = event_log_df.astype(str).to_dict(orient='records')

        return {
            "status": "success",
            "metrics": metrics_dict,
            "plot_html": plot_html, 
            "event_log": event_log_dict
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
from core.optimization import Optimizer, OptimizationResult

class OptimizationRequest(BaseModel):
    code: str
    ranges: Dict[str, Dict[str, float]] # param -> {min, max, step}
    algorithm: str # "annealing" or "hill_climb"
    target_metric: str = "total_net_profit"
    # Backtest params
    start_date: str
    end_date: str
    initial_balance: float = 10000.0
    slippage: float = 0.01
    broker_fee: float = 0.0
    annual_interest_rate: float = 0.0
    base_params: Dict[str, Any] = {}

@app.post("/optimize")
async def run_optimization(request: OptimizationRequest):
    try:
        # 1. Parse dates and compile strategy once if possible
        start_dt = pd.to_datetime(request.start_date)
        end_dt = pd.to_datetime(request.end_date)
        
        # Strategy Compilation Logic (Reused)
        strategy_cls = None
        if request.code:
            try:
                local_scope = {}
                exec(request.code, globals(), local_scope)
                if 'Strategy' in local_scope:
                    strategy_cls = local_scope['Strategy']
                else:
                    import inspect
                    classes = [obj for name, obj in local_scope.items() if inspect.isclass(obj)]
                    if classes:
                        strategy_cls = classes[0]
                    else:
                        raise ValueError("No strategy class found")
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Error compiling strategy: {str(e)}")
        else:
             strategy_cls = SimpleTestStrategy

        # 2. Define Objective Function
        def objective_function(params: Dict[str, Any]) -> Dict[str, float]:
            # Merge optimized params with base params
            full_params = {**request.base_params, **params}
            
            engine = BacktestEngineWithSource(
                data_source_func=duckdb_datasource, 
                start_time=start_dt,
                end_time=end_dt,
                interval=pd.Timedelta(days=1), 
                strategy_cls=strategy_cls, 
                initial_money=request.initial_balance,
                slippage=request.slippage,
                broker_fee=request.broker_fee,
                annual_interest_rate=request.annual_interest_rate,
                execution_delay=0,
                strategy_params=full_params
            )
            
            try:
                event_log = engine.run()
                metrics_df = analyze_portfolio(event_log)
                if metrics_df is not None and not metrics_df.empty:
                    return metrics_df.to_dict(orient='records')[0]
                return {}
            except Exception:
                return {}

        # 3. Initialize Optimizer
        optimizer = Optimizer(objective_function, target_metric=request.target_metric)
        
        # 4. Run Algorithm
        initial_params = {}
        for param, config in request.ranges.items():
            # Start at midpoint
            initial_params[param] = (config['min'] + config['max']) / 2
            if config.get('type') == 'int':
                initial_params[param] = int(initial_params[param])

        results = []
        if request.algorithm == "annealing":
            results = optimizer.simulated_annealing(initial_params, request.ranges, iterations=20) # 20 iterations for responsiveness
        elif request.algorithm == "hill_climb":
            results = optimizer.hill_climbing(initial_params, request.ranges, iterations=20)
        
        return {
            "status": "success",
            "results": [
                {
                    "params": r.params,
                    "metrics": r.metrics,
                    "score": r.score
                }
                for r in results
            ]
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/backtest/last-log")
async def get_last_log():
    df = last_backtest_results.get("event_log")
    if df is None:
        return {"event_log": []}
    return {"event_log": df.astype(str).to_dict(orient='records')}

@app.get("/ticker/{ticker}/ohlc")
async def get_ticker_ohlc(ticker: str):
    """
    Fetch OHLC data for a specific ticker across a broad date range from DuckDB.
    """
    try:
        # Use a wide range to capture all history
        start_time = "2010-01-01" 
        end_time = datetime.now().strftime("%Y-%m-%d")
        
        ds = DailyOHLCSource()
        # DailyOHLCSource returns a DataFrame with: timestamp, ticker, open, high, low, close, volume (and others per query)
        # We need to filter for the specific ticker because DailyOHLCSource queries ALL matching globs
        # But wait, DailyOHLCSource.query takes target_globs which are constructed from date range.
        # It queries *everything* in that range.
        # DuckDB filtered query is more efficient.
        # However, BaseDuckDBSource constructs globs based on date.
        # And the query groups by ticker.
        # So it returns ALL tickers. That's inefficient if we just want one.
        # But the current implementation of BaseDuckDBSource doesn't support filtering by ticker in _get_target_globs (it uses symbol=*).
        # We can filter in the SQL query!
        # But DailyOHLCSource.query doesn't take a ticker argument.
        # We should use the returned DF and filter it. The DF might be huge.
        
        # Let's instantiate and call a custom query method? Or filter after?
        # A better approach is to modify DailyOHLCSource to accept a ticker filter or add a method.
        # But for now, let's filter the DF. If it's too slow, we'll optimizing sources.py.
        # Actually, get_ticker_ohlc is often called for a specific view.
        # Let's see if we can optimize later. For now, filter the DF.
        
        df = ds.query(start_time, end_time)
        
        if df.empty:
            return []
            
        ticker_df = df[df['ticker'] == ticker]
        
        if ticker_df.empty:
            return []
            
        # Format for frontend
        all_data = []
        for row in ticker_df.itertuples():
            all_data.append({
                "time": int(row.timestamp.timestamp()),
                "open": float(row.open),
                "high": float(row.high),
                "low": float(row.low),
                "close": float(row.close)
            })
            
        return all_data
        
    except Exception as e:
        print(f"Error in get_ticker_ohlc: {e}")
        return []

# --- ML Model Management ---

class TrainRequest(BaseModel):
    name: str
    code: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None

@app.get("/models")
async def list_models():
    """List available models in the data/ directory."""
    if not os.path.exists("data"):
        return []
    
    files = []
    try:
        for f in os.listdir("data"):
            if os.path.isfile(os.path.join("data", f)) and not f.startswith('.'):
                files.append(f)
    except Exception:
        pass
    return sorted(files)

@app.post("/train")
async def train_model(request: TrainRequest):
    """
    Execute python code to train a model.
    Injects 'save_model(obj)' into the local scope.
    """
    os.makedirs("data", exist_ok=True)
    output_buffer = io.StringIO()
    
    def save_model(obj, filename=None):
        import pickle
        fname = filename or request.name
        if "." not in fname:
            fname += ".pkl"
        path = os.path.join("data", fname)
        with open(path, 'wb') as f:
            pickle.dump(obj, f)
        print(f"Model saved to {path}")

    # Fetch data if dates provided
    training_data = pd.DataFrame()
    if request.start_date and request.end_date:
        try:
            print(f">>> Fetching training data from {request.start_date} to {request.end_date}...")
            training_data = duckdb_datasource(request.start_date, request.end_date)
            print(f">>> Fetched {len(training_data)} rows of data.")
        except Exception as e:
            print(f">>> Error fetching data: {e}")

    # Inject useful globals
    local_scope = {
        "save_model": save_model,
        "pd": pd,
        "np": np,
        "data": training_data
    }

    try:
        with redirect_stdout(output_buffer):
            print(f">>> ML Studio: Starting training for '{request.name}'...")
            # Execute the training code
            exec(request.code, globals(), local_scope)
            print(">>> Training session completed.")
            
        return {
            "status": "success", 
            "output": output_buffer.getvalue()
        }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "output": output_buffer.getvalue()
        }

# --- SQL Snippets Management ---

SQL_SNIPPETS_DIR = "resources/sql_snippets"
os.makedirs(SQL_SNIPPETS_DIR, exist_ok=True)
# Ensure General category exists
os.makedirs(os.path.join(SQL_SNIPPETS_DIR, "General"), exist_ok=True)

class SQLSnippetModel(BaseModel):
    name: str
    category: str = "General"
    code: str

@app.get("/sql-snippets")
async def list_sql_snippets():
    """
    Returns a dictionary of categories to list of snippets.
    {
        "General": [ { "name": "all_trades", "code": "SELECT * ...", "path": "General/all_trades.sql" } ],
        "Other": ...
    }
    """
    snippets = {}
    
    # Walk through the directory
    for root, dirs, files in os.walk(SQL_SNIPPETS_DIR):
        category = os.path.relpath(root, SQL_SNIPPETS_DIR)
        if category == ".":
            category = "Uncategorized"
        
        snippet_list = []
        for f in files:
            if f.endswith(".sql"):
                try:
                    full_path = os.path.join(root, f)
                    with open(full_path, 'r') as file:
                        code = file.read()
                    
                    name = f.replace(".sql", "")
                    snippet_list.append({
                        "name": name,
                        "code": code,
                        "path": os.path.join(category, f),
                        "date": datetime.fromtimestamp(os.path.getmtime(full_path)).isoformat()
                    })
                except Exception:
                    continue
        
        if snippet_list:
            # Sort by date
            snippet_list.sort(key=lambda x: x['date'], reverse=True)
            snippets[category] = snippet_list
            
    return snippets

@app.post("/sql-snippets")
async def save_sql_snippet(snippet: SQLSnippetModel):
    # Sanitize inputs
    safe_cat = "".join([c for c in snippet.category if c.isalpha() or c.isdigit() or c in (' ', '_', '-')]).strip() or "General"
    safe_name = "".join([c for c in snippet.name if c.isalpha() or c.isdigit() or c in (' ', '_', '-')]).strip()
    
    if not safe_name:
        raise HTTPException(status_code=400, detail="Invalid snippet name")
        
    category_dir = os.path.join(SQL_SNIPPETS_DIR, safe_cat)
    os.makedirs(category_dir, exist_ok=True)
    
    file_path = os.path.join(category_dir, f"{safe_name}.sql")
    
    try:
        with open(file_path, 'w') as file:
            file.write(snippet.code)
        return {"status": "success", "message": f"Saved {safe_cat}/{safe_name}", "category": safe_cat}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

