# core/api.py

import pandas as pd
import numpy as np
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

from core.engine import BacktestEngineWithSource, plot_simulation_trades
from core.analysis import analyze_portfolio
from core.context import Context 

app = FastAPI()

class BacktestRequest(BaseModel):
    start_date: str  
    end_date: str    
    initial_balance: float = 10000.0
    slippage: float = 0.01
    strategy_params: Dict[str, Any] = {}

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

def mock_data_source(start_time, end_time) -> pd.DataFrame:
    dates = pd.date_range(start=start_time, end=end_time, freq='1H') 
    if len(dates) == 0:
        return pd.DataFrame()
    
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(len(dates)))
    
    df = pd.DataFrame({
        'timestamp': dates,
        'ticker': 'TEST_ASSET',
        'price': prices,
        'volume': np.random.randint(100, 1000, size=len(dates))
    })
    return df

@app.post("/run-backtest")
async def run_backtest_endpoint(request: BacktestRequest):
    try:
        start_dt = pd.to_datetime(request.start_date)
        end_dt = pd.to_datetime(request.end_date)
        engine = BacktestEngineWithSource(
            data_source_func=mock_data_source, 
            start_time=start_dt,
            end_time=end_dt,
            interval=pd.Timedelta(days=1), 
            strategy_cls=SimpleTestStrategy, 
            initial_money=request.initial_balance,
            slippage=request.slippage,
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
            "event_log_summary": event_log_dict[:50] 
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
