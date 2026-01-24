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

from core.engine import BacktestEngineWithSource, plot_simulation_trades, filesystem_datasource
from core.analysis import analyze_portfolio
from core.context import Context 

app = FastAPI()

class StrategyModel(BaseModel):
    name: str
    code: str
    params: Dict[str, Any]
    date: Optional[str] = None

STRATEGIES_DIR = "strategies"
os.makedirs(STRATEGIES_DIR, exist_ok=True)

@app.get("/strategies")
async def list_strategies():
    strategies = []
    files = glob.glob(os.path.join(STRATEGIES_DIR, "*.json"))
    for f in files:
        try:
            with open(f, 'r') as file:
                data = json.load(file)
                strategies.append({
                    "name": data.get("name"),
                    "date": data.get("date", ""),
                })
        except Exception:
            continue
    return strategies

@app.get("/strategies/{name}")
async def get_strategy(name: str):
    file_path = os.path.join(STRATEGIES_DIR, f"{name}.json")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/strategies")
async def save_strategy(strategy: StrategyModel):
    file_path = os.path.join(STRATEGIES_DIR, f"{strategy.name}.json")
    
    # Store with current date if not provided
    data = strategy.dict()
    if not data.get('date'):
        data['date'] = datetime.now().isoformat()
        
    try:
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)
        return {"status": "success", "message": f"Saved {strategy.name}"}
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
            invest_amount = context.balance * 0.10 # Invest 10%
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
            data_source_func=filesystem_datasource,
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

        metrics_df = analyze_portfolio(event_log_df)
        
        fig = plot_simulation_trades(event_log_df)
        plot_json = fig.to_json()

        metrics_dict = metrics_df.to_dict(orient='records')[0] if metrics_df is not None else {}
        
        event_log_dict = event_log_df.astype(str).to_dict(orient='records')

        return {
            "status": "success",
            "metrics": metrics_dict,
            "plot_json": json.loads(plot_json), 
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
                data_source_func=filesystem_datasource, 
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
