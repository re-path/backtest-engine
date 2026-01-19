# core/engine.py
import math
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import concurrent.futures
import sys
import os
import contextlib
import itertools
import plotly.express as px
from tqdm import tqdm
from typing import List, Dict, Any, Optional, Union, Set, Tuple, Type
from core.context import Context

class BacktestEngineWithSource:
    def __init__(self, data_source_func, start_time, end_time, interval, strategy_cls, initial_money=100, slippage=0.20, broker_fee=0.0, annual_interest_rate=0.0, execution_delay=0, strategy_params=None):
        self.data_source_func = data_source_func
        self.start_time = pd.to_datetime(start_time)
        self.end_time = pd.to_datetime(end_time)
        self.interval = interval
        
        if strategy_params is None:
            strategy_params = {}
            
        self.strategy = strategy_cls(**strategy_params)
        self.event_log = []
        
        self.context = Context(initial_money, slippage, self.event_log, execution_delay=execution_delay, broker_fee=broker_fee, annual_interest_rate=annual_interest_rate)
        self.last_known_prices = {}

    def run(self):
        total_chunks = int((self.end_time - self.start_time) / self.interval)
        pbar = tqdm(total=total_chunks, desc="Backtesting")
        self.event_log.append({
            "timestamp": self.start_time,
            "event_type": "START",
            "ticker": None,
            "price": None,
            "money_change": 0.0,
            "portfolio_balance": self.context.get_balance()
        })

        current_time = self.start_time
        
        while current_time < self.end_time:
            next_time = min(current_time + self.interval, self.end_time)
            chunk_df = self.data_source_func(current_time, next_time)
            
            if not chunk_df.empty:
                chunk_df = chunk_df.sort_values(by=['timestamp', 'ticker'])
                for row in chunk_df.itertuples(index=False):
                    bar = row
                    self.context.process_pending_orders(bar.ticker, bar.price, bar.timestamp)
                    self.strategy.on_bar(self.context, bar)
                    self.last_known_prices[bar.ticker] = bar.price

            pbar.update(1)
            current_time = next_time
        
        pbar.close()
        return pd.DataFrame(self.event_log)

def backtest_streamed(
        data_source_func: Any,
        start_time: pd.Timestamp = pd.Timestamp('2025-06-01'),
        end_time: pd.Timestamp = pd.Timestamp('2025-06-02'),
        strategy: Any = None, 
        slippage: float = 0.00,
        initial_money: float = 100.0,
        execution_delay: float = 0.00,
        strategy_params: Dict[str, Any] = {}
    ) -> Tuple[Any, Optional[pd.DataFrame]]:
    
    # Assuming BacktestEngineWithSource is imported or defined elsewhere
    engine: Any = BacktestEngineWithSource( 
        data_source_func=data_source_func,
        start_time=start_time,
        end_time=end_time,
        interval=pd.Timedelta(days=4),
        strategy_cls=strategy,
        initial_money=initial_money, 
        slippage=slippage,
        execution_delay=execution_delay,
        strategy_params=strategy_params
    )

    event_log: Any = engine.run()
    # Assuming event_log is converted to DataFrame inside analyze_portfolio or engine returns DataFrame
    analysis_results: Optional[pd.DataFrame] = analyze_portfolio(event_log)
    fig: Any = plot_simulation_trades(event_log)
    fig.show()
    
    return event_log, analysis_results

def plot_simulation_trades(event_log_df):
    if event_log_df.empty:
        return go.Figure()

    df = event_log_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
        try:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        except:
            df['timestamp'] = pd.to_datetime(df['timestamp'])

    df = df[df['ticker'].notna()]
    df = df.sort_values(by=['ticker', 'timestamp'])

    entries = df[df['event_type'] == 'BUY']
    partials = df[df['event_type'].isin(['SELL', 'SELL-MOON'])]
    exits = df[df['event_type'].isin(['STOP', 'TIME_EXIT', 'LIQUIDATE', 'CLOSE'])]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    line_x = []
    line_y = []
    for ticker, group in df.groupby("ticker"):
        line_x.extend(group["timestamp"])
        line_y.extend(group["price"])
        line_x.append(None)
        line_y.append(None)

    fig.add_trace(go.Scatter(
        x=line_x, y=line_y, mode="lines", name="Trade Path",
        line=dict(color="grey", width=1, dash="dot"), hoverinfo="none"
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=entries["timestamp"], y=entries["price"], mode="markers", name="Entry",
        customdata=entries[["ticker", "money_change"]],
        marker=dict(color="#00ff00", size=8, symbol="circle", line=dict(width=1, color="white")),
        hovertemplate="<b>ENTRY</b><br>ticker: %{customdata[0]}<br>Cost: %{customdata[1]:.2f} RS<br>Time: %{x}<br>price: %{y:,.0f}<extra></extra>"
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=partials["timestamp"], y=partials["price"], mode="markers", name="Partial Profit",
        customdata=partials[["ticker", "event_type", "money_change"]],
        marker=dict(color="#00bfff", size=7, symbol="diamond"),
        hovertemplate="<b>PARTIAL</b><br>ticker: %{customdata[0]}<br>Type: %{customdata[1]}<br>Return: +%{customdata[2]:.2f} RS<br>Time: %{x}<br>price: %{y:,.0f}<extra></extra>"
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=exits["timestamp"], y=exits["price"], mode="markers", name="Closed",
        customdata=exits[["ticker", "event_type", "money_change"]],
        marker=dict(color="#ff3333", size=8, symbol="x", line=dict(width=2)),
        hovertemplate="<b>CLOSED</b><br>ticker: %{customdata[0]}<br>Reason: %{customdata[1]}<br>Return: +%{customdata[2]:.2f} RS<br>Time: %{x}<br>price: %{y:,.0f}<extra></extra>"
    ), secondary_y=False)

    balance_df = df.sort_values(by='timestamp')

    fig.add_trace(go.Scatter(
        x=balance_df['timestamp'], 
        y=balance_df['portfolio_balance'],
        mode='lines',
        name='Portfolio Balance',
        line=dict(color='rgba(0, 255, 0, 0.5)', width=1), # Thin green line
        fill='tozeroy',                                   # Fills area to bottom
        fillcolor='rgba(0, 255, 0, 0.1)',                 # Very transparent green background
    ), secondary_y=True)                                  # <--- Puts it on Right Y-Axis

    fig.update_layout(
        title="Portfolio Simulation",
        template="plotly_dark",
         height=700, width=1500,
        yaxis2=dict(title="Portfolio Balance (RS)", showgrid=False)
    )
    return fig