# core/engine.py
import math
import pandas as pd
import numpy as np
import polars as pl
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


def filesystem_datasource(start_time, end_time):
    start_date = pd.to_datetime(start_time)
    end_date = pd.to_datetime(end_time)
    dates = pd.date_range(start=start_date, end=end_date - pd.Timedelta(seconds=1), freq='D')
    
    dfs = []
    base_path = "data/old_data"
    
    for date in dates:
        year = str(date.year)
        date_str = date.strftime('%Y-%m-%d')
        file_path = os.path.join(base_path, year, f"{date_str}.csv")
        
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path, thousands=',')
                if 'Symbol' in df.columns:
                    df = df.rename(columns={'Symbol': 'ticker'})
                
                if 'Close' in df.columns:
                    df = df.rename(columns={'Close': 'price'})
                
                df['timestamp'] = date
                
                
                dfs.append(df)
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
                
    if not dfs:
        return pd.DataFrame(columns=['timestamp', 'ticker', 'price'])
        
    return pd.concat(dfs, ignore_index=True)

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
        data_source_func: Any = filesystem_datasource,
        start_time: pd.Timestamp = pd.Timestamp('2020-01-01'),
        end_time: pd.Timestamp = pd.Timestamp('2020-02-01'),
        strategy: Any = None, 
        slippage: float = 0.00,
        initial_money: float = 100.0,
        execution_delay: float = 0.00,
        strategy_params: Dict[str, Any] = {}
    ) -> Tuple[Any, Optional[pd.DataFrame]]:
    
    # Local import to avoid circular dependency
    from core.analysis import analyze_portfolio

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
    
    # 1. Standardize Timestamps
    if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', errors='coerce')
        if df['timestamp'].isna().all():
            df['timestamp'] = pd.to_datetime(event_log_df['timestamp'], errors='coerce')

    # 2. Hard Numeric Conversion
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    df['portfolio_balance'] = pd.to_numeric(df['portfolio_balance'], errors='coerce')
    
    # 3. THE FIX: Kill the zero-price garbage that creates the bottom-trails
    # This ensures the trail only exists where the dots exist
    df = df.dropna(subset=['ticker', 'price', 'timestamp'])
    df = df[df['price'] > 1e-8] # Filters out actual 0.0 values
    
    df = df.sort_values(by=['ticker', 'timestamp'])

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 4. Generate Dynamic Color Map for Dots
    unique_events = df['event_type'].unique()
    palette = px.colors.qualitative.Alphabet + px.colors.qualitative.Dark24
    color_map = {}
    for i, event in enumerate(unique_events):
        evt_str = str(event).lower()
        if 'buy' in evt_str:
            color_map[event] = '#00FF00' # Bright Green
        elif 'sell' in evt_str or 'take' in evt_str:
            color_map[event] = '#00BFFF' # Blue
        elif any(x in evt_str for x in ['stop', 'liquidate', 'exit', 'close', 'loss']):
            color_map[event] = '#FF3333' # Red
        else:
            color_map[event] = palette[i % len(palette)]

    # 5. Trails: Connected PER TICKER using the cleaned price
    for ticker in df['ticker'].unique():
        ticker_data = df[df['ticker'] == ticker]
        fig.add_trace(go.Scatter(
            x=ticker_data['timestamp'],
            y=ticker_data['price'],
            mode='lines',
            name=f'Trail: {ticker}',
            line=dict(color='rgba(200, 200, 200, 0.3)', width=1, dash='dot'),
            showlegend=False,
            hoverinfo='skip',
            connectgaps=False
        ), secondary_y=False)

    # 6. Dots: Each event type gets its own color
    for event_type in unique_events:
        event_data = df[df['event_type'] == event_type]
        fig.add_trace(go.Scatter(
            x=event_data['timestamp'],
            y=event_data['price'],
            mode='markers',
            name=str(event_type),
            customdata=event_data[['ticker', 'money_change']],
            marker=dict(
                color=color_map[event_type], 
                size=8, 
                line=dict(width=0.5, color='white'),
                opacity=0.8
            ),
            hovertemplate="<b>" + str(event_type) + "</b><br>Tkr: %{customdata[0]}<br>Px: %{y}<br>Chg: %{customdata[1]}<extra></extra>"
        ), secondary_y=False)

    # 7. Portfolio Balance (Area chart on right axis)
    balance_df = df.sort_values('timestamp').drop_duplicates('timestamp', keep='last')
    fig.add_trace(go.Scatter(
        x=balance_df['timestamp'],
        y=balance_df['portfolio_balance'],
        mode='lines',
        name='Portfolio Balance',
        line=dict(color='rgba(255, 255, 255, 0.4)', width=1.5),
        fill='tozeroy',
        fillcolor='rgba(100, 100, 100, 0.1)'
    ), secondary_y=True)

    fig.update_layout(
        template="plotly_dark",
        height=800,
        width=1600,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        xaxis=dict(showgrid=False),
        yaxis=dict(title="Execution Price", side="left", showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
        yaxis2=dict(title="Portfolio Balance", side="right", showgrid=False)
    )

    return fig