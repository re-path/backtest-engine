
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
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

last_backtest_results = {
    "event_log": None,
    "custom_metrics": {}
}

class StrategyModel(BaseModel):
    name: str
    code: str
    params: Dict[str, Any]
    date: Optional[str] = None


STRATEGIES_DIR = os.getenv("STRATEGIES_DIR", "resources/strategies")
os.makedirs(STRATEGIES_DIR, exist_ok=True)

@app.get("/strategies")
async def list_strategies():
    strategies = []
    files = glob.glob(os.path.join(STRATEGIES_DIR, "*.py"))
    for f in files:
        try:
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
            return {
                "name": name,
                "code": code,
                "params": {} 
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/strategies")
async def save_strategy(strategy: StrategyModel):
    safe_name = "".join([c for c in strategy.name if c.isalpha() or c.isdigit() or c in (' ', '_', '-')]).rstrip()
    if not safe_name:
        raise HTTPException(status_code=400, detail="Invalid strategy name")
        
    file_path = os.path.join(STRATEGIES_DIR, f"{safe_name}.py")
    
    try:
        with open(file_path, 'w') as file:
            file.write(strategy.code)
        return {"status": "success", "message": f"Saved {safe_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


NOTEBOOKS_DIR = os.getenv("NOTEBOOKS_DIR", "resources/notebooks")
os.makedirs(NOTEBOOKS_DIR, exist_ok=True)

class NotebookModel(BaseModel):
    name: str

class RenameNotebookModel(BaseModel):
    old_name: str
    new_name: str

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

@app.post("/notebooks/rename")
async def rename_notebook(notebook: RenameNotebookModel):
    old_safe = "".join([c for c in notebook.old_name if c.isalpha() or c.isdigit() or c in (' ', '_', '-')]).rstrip()
    new_safe = "".join([c for c in notebook.new_name if c.isalpha() or c.isdigit() or c in (' ', '_', '-')]).rstrip()
    
    if not old_safe or not new_safe:
        raise HTTPException(status_code=400, detail="Invalid notebook name")
        
    old_path = os.path.join(NOTEBOOKS_DIR, f"{old_safe}.py")
    new_path = os.path.join(NOTEBOOKS_DIR, f"{new_safe}.py")
    
    if not os.path.exists(old_path):
        raise HTTPException(status_code=404, detail="Notebook not found")
        
    if os.path.exists(new_path):
        raise HTTPException(status_code=400, detail="Target name already exists")
    
    try:
        os.rename(old_path, new_path)
        return {"status": "success", "message": f"Renamed {old_safe} to {new_safe}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class BacktestRequest(BaseModel):
    start_date: str  
    end_date: str    
    initial_balance: float = float(os.getenv("INITIAL_BALANCE", 10000.0))
    slippage: float = float(os.getenv("DEFAULT_SLIPPAGE", 0.01))
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
            invest_amount = context.get_balance() * 0.10
            context.buy(bar.ticker, invest_amount, bar.price, bar.timestamp)
        elif bar.price < last_price:
            context.close(bar.ticker, bar.price, bar.timestamp, "TrendRev")
        
        context.set_state('last_price', bar.price)

@app.post("/run-backtest")
async def run_backtest_endpoint(request: BacktestRequest):
    try:
        start_dt = pd.to_datetime(request.start_date)
        end_dt = pd.to_datetime(request.end_date)

        strategy_cls = SimpleTestStrategy
        
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
                        raise ValueError("No strategy class found in the provided code. Please name your class 'Strategy'.")
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Error compiling strategy: {str(e)}")

        engine = BacktestEngineWithSource(
            data_source_func=duckdb_datasource,
            start_time=start_dt,
            end_time=end_dt,
            interval=pd.Timedelta(days=30), 
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

        last_backtest_results["event_log"] = event_log_df
        last_backtest_results["custom_metrics"] = engine.context.custom_metrics

        metrics_df = analyze_portfolio(event_log_df)
        
        fig = plot_simulation_trades(event_log_df)
        plot_html = fig.to_html(full_html=False, include_plotlyjs=True)

        metrics_dict = metrics_df.to_dict(orient='records')[0] if metrics_df is not None else {}
        
        event_log_dict = event_log_df.astype(str).to_dict(orient='records')

        return {
            "status": "success",
            "metrics": metrics_dict,
            "plot_html": plot_html, 
            "event_log": event_log_dict,
            "custom_metrics": engine.context.custom_metrics
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

from core.optimization import Optimizer, OptimizationResult

class OptimizationRequest(BaseModel):
    code: str
    ranges: Dict[str, Dict[str, float]]
    algorithm: str
    target_metric: str = "total_net_profit"
    start_date: str
    end_date: str
    initial_balance: float = float(os.getenv("INITIAL_BALANCE", 10000.0))
    slippage: float = float(os.getenv("DEFAULT_SLIPPAGE", 0.01))
    broker_fee: float = 0.0
    annual_interest_rate: float = 0.0
    base_params: Dict[str, Any] = {}

@app.post("/optimize")
async def run_optimization(request: OptimizationRequest):
    try:
        start_dt = pd.to_datetime(request.start_date)
        end_dt = pd.to_datetime(request.end_date)
        
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

        def objective_function(params: Dict[str, Any]) -> Dict[str, float]:
            full_params = {**request.base_params, **params}
            
            engine = BacktestEngineWithSource(
                data_source_func=duckdb_datasource, 
                start_time=start_dt,
                end_time=end_dt,
                interval=pd.Timedelta(days=30), 
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

        optimizer = Optimizer(objective_function, target_metric=request.target_metric)
        
        initial_params = {}
        for param, config in request.ranges.items():
            initial_params[param] = (config['min'] + config['max']) / 2
            if config.get('type') == 'int':
                initial_params[param] = int(initial_params[param])

        results = []
        if request.algorithm == "annealing":
            results = optimizer.simulated_annealing(initial_params, request.ranges, iterations=20)
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
    custom = last_backtest_results.get("custom_metrics", {})
    if df is None:
        return {"event_log": [], "custom_metrics": {}}
    return {
        "event_log": df.astype(str).to_dict(orient='records'),
        "custom_metrics": custom
    }

@app.get("/ticker/{ticker}/ohlc")
async def get_ticker_ohlc(ticker: str):
    try:
        start_time = "2010-01-01" 
        end_time = datetime.now().strftime("%Y-%m-%d")
        
        ds = DailyOHLCSource()
        
        df = ds.query(start_time, end_time)
        
        if df.empty:
            return []
            
        ticker_df = df[df['ticker'] == ticker]
        
        if ticker_df.empty:
            return []
            
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


class TrainRequest(BaseModel):
    name: str
    code: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None

@app.get("/models")
async def list_models():
    MODELS_DIR = os.getenv("MODELS_DIR", "data")
    if not os.path.exists(MODELS_DIR):
        return []
    
    files = []
    try:
        for f in os.listdir(MODELS_DIR):
            if os.path.isfile(os.path.join(MODELS_DIR, f)) and not f.startswith('.'):
                files.append(f)
    except Exception:
        pass
    return sorted(files)

@app.post("/train")
async def train_model(request: TrainRequest):
    MODELS_DIR = os.getenv("MODELS_DIR", "data")
    os.makedirs(MODELS_DIR, exist_ok=True)
    output_buffer = io.StringIO()
    
    def save_model(obj, filename=None):
        import pickle
        fname = filename or request.name
        if "." not in fname:
            fname += ".pkl"
        path = os.path.join(MODELS_DIR, fname)
        with open(path, 'wb') as f:
            pickle.dump(obj, f)
        print(f"Model saved to {path}")

    training_data = pd.DataFrame()
    if request.start_date and request.end_date:
        try:
            print(f">>> Fetching training data from {request.start_date} to {request.end_date}...")
            training_data = duckdb_datasource(request.start_date, request.end_date)
            print(f">>> Fetched {len(training_data)} rows of data.")
        except Exception as e:
            print(f">>> Error fetching data: {e}")

    local_scope = {
        "save_model": save_model,
        "pd": pd,
        "np": np,
        "data": training_data
    }

    try:
        with redirect_stdout(output_buffer):
            print(f">>> ML Studio: Starting training for '{request.name}'...")
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


SQL_SNIPPETS_DIR = os.getenv("SQL_SNIPPETS_DIR", "resources/sql_snippets")
os.makedirs(SQL_SNIPPETS_DIR, exist_ok=True)
os.makedirs(os.path.join(SQL_SNIPPETS_DIR, "General"), exist_ok=True)

class SQLSnippetModel(BaseModel):
    name: str
    category: str = "General"
    code: str

@app.get("/sql-snippets")
async def list_sql_snippets():
    snippets = {}
    
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
            snippet_list.sort(key=lambda x: x['date'], reverse=True)
            snippets[category] = snippet_list
            
    return snippets

@app.post("/sql-snippets")
async def save_sql_snippet(snippet: SQLSnippetModel):
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


class LiveStrategyRequest(BaseModel):
    strategy_name: str

@app.get("/live/strategies")
async def list_live_strategies():
    import redis
    
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6380))
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    
    strategies = []
    files = glob.glob(os.path.join(STRATEGIES_DIR, "*.py"))
    for f in files:
        name = os.path.basename(f).replace(".py", "")
        status = r.get(f"strategy:{name}:status") or "stopped"
        strategies.append({
            "name": name,
            "status": status,
            "date": datetime.fromtimestamp(os.path.getmtime(f)).isoformat()
        })
    
    return sorted(strategies, key=lambda x: x['name'])

@app.post("/live/strategies/start")
async def start_live_strategy(request: LiveStrategyRequest):
    import subprocess
    import redis
    
    strategy_name = request.strategy_name
    
    strategy_path = os.path.join(STRATEGIES_DIR, f"{strategy_name}.py")
    if not os.path.exists(strategy_path):
        raise HTTPException(status_code=404, detail="Strategy file not found")
        
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6380))
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    status = r.get(f"strategy:{strategy_name}:status")
    if status == "running":
        return {"status": "success", "message": "Strategy already running"}
        
    cmd_str = f"uv run python -m core.live_runner --strategy {strategy_name}"
    
    print(f"Launching strategy {strategy_name} with command: {cmd_str}")
    
    try:
        full_cmd = ["ksai_proc", "--name", strategy_name, "--"] + cmd_str.split()
        
        subprocess.run(full_cmd, check=True)
        
        import time
        for _ in range(5):
            time.sleep(0.5)
            status = r.get(f"strategy:{strategy_name}:status")
            if status == "running":
                return {"status": "success", "message": f"Strategy {strategy_name} started"}
        
        return {"status": "warning", "message": "Strategy process launched but status not yet 'running' in Redis"}
        
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Failed to launch process: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/live/strategies/stop")
async def stop_live_strategy(request: LiveStrategyRequest):
    import subprocess
    import redis
    
    strategy_name = request.strategy_name
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6380))
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    
    r.set(f"strategy:{strategy_name}:status", "stopping")
    
    try:
        cmd = ["ksai_proc", "stop", "--name", strategy_name]
        subprocess.run(cmd, check=True)
        
        r.set(f"strategy:{strategy_name}:status", "stopped")
        
        return {"status": "success", "message": f"Strategy {strategy_name} stopped"}
        
    except subprocess.CalledProcessError as e:
         raise HTTPException(status_code=500, detail=f"Failed to stop process: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
