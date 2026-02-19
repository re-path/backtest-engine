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
from core.engine import *

def analyze_portfolio(event_log_df: pd.DataFrame) -> Optional[pd.DataFrame]:
    if event_log_df.empty:
        return None

    start_balance: float = float(event_log_df.iloc[0]['portfolio_balance'])
    end_balance: float = float(event_log_df.iloc[-1]['portfolio_balance'])
    total_return_pct: float = (end_balance / start_balance - 1) * 100 if start_balance > 0 else 0.0
    
    print(f"Start Portfolio: {start_balance:.2f} money")
    print(f"End Portfolio:   {end_balance:.2f} money")
    print(f"Total Return:    {total_return_pct:.2f}%")

    df: pd.DataFrame = event_log_df.copy()
    trade_events: pd.DataFrame = df[df['ticker'].notna()]
    trades: pd.DataFrame = trade_events.groupby('ticker').agg({
        'money_change': 'sum',
        'timestamp': ['min', 'max'] 
    })
    trades.columns = pd.Index(['pnl', 'entry_time', 'exit_time'])
    trades = trades.sort_values(by='exit_time') 
    
    wins: pd.DataFrame = trades[trades['pnl'] > 0]
    losses: pd.DataFrame = trades[trades['pnl'] <= 0]

    total_trades: int = len(trades)
    num_winning: int = len(wins)
    num_losing: int = len(losses)
    
    gross_profit: float = wins['pnl'].sum()
    gross_loss: float = losses['pnl'].sum()
    total_net_profit: float = gross_profit + gross_loss 
    
    avg_win: float = wins['pnl'].mean() if num_winning > 0 else 0.0
    avg_loss: float = losses['pnl'].mean() if num_losing > 0 else 0.0
    avg_trade: float = trades['pnl'].mean()
    
    profit_factor: float = gross_profit / abs(gross_loss) if gross_loss != 0 else 0.0
    
    largest_win: float = wins['pnl'].max() if not wins.empty else 0.0
    largest_loss: float = losses['pnl'].min() if not losses.empty else 0.0

    current_win_streak: int = 0
    current_loss_streak: int = 0
    max_win_streak: int = 0
    max_loss_streak: int = 0
    
    cur_win_start: Any = None
    cur_loss_start: Any = None
    max_win_dates: Tuple[Any, Any] = (None, None) 
    max_loss_dates: Tuple[Any, Any] = (None, None) 

    for row in trades.itertuples():
        if row.pnl > 0:
            if current_win_streak == 0:
                cur_win_start = row.entry_time 
            
            current_win_streak += 1
            current_loss_streak = 0
            cur_loss_start = None
            
            if current_win_streak > max_win_streak:
                max_win_streak = current_win_streak
                max_win_dates = (cur_win_start, row.exit_time) 
        else:
            if current_loss_streak == 0:
                cur_loss_start = row.entry_time
                
            current_loss_streak += 1
            current_win_streak = 0
            cur_win_start = None
            
            if current_loss_streak > max_loss_streak:
                max_loss_streak = current_loss_streak
                max_loss_dates = (cur_loss_start, row.exit_time)

    def fmt_dates(date_tuple: Tuple[Any, Any]) -> str:
        if not date_tuple or not date_tuple[0]:
            return ""
        s = pd.to_datetime(date_tuple[0]).strftime('%Y-%m-%d')
        e = pd.to_datetime(date_tuple[1]).strftime('%Y-%m-%d')
        return f"({s} to {e})"

    win_streak_str: str = fmt_dates(max_win_dates)
    loss_streak_str: str = fmt_dates(max_loss_dates)

    num_even: int = len(trades[trades['pnl'] == 0])

    largest_win_pct_gross: float = (largest_win / gross_profit * 100) if gross_profit > 0 else 0.0
    largest_loss_pct_gross: float = (largest_loss / gross_loss * 100) if gross_loss != 0 else 0.0

    print("-" * 50)
    print("PERFORMANCE SUMMARY")
    print("-" * 50)
    print(f"{'Total Net Profit':<25} {total_net_profit:>15.2f} money")
    print(f"{'Gross Profit':<25} {gross_profit:>15.2f} money")
    print(f"{'Gross Loss':<25} {gross_loss:>15.2f} money")
    print(f"{'Profit Factor':<25} {profit_factor:>15.3f}")
    print("-" * 50)
    print(f"{'Total Number of Trades':<25} {total_trades:>15}")
    print(f"{'Percent of Profitable Trades':<25} {(num_winning/total_trades*100) if total_trades else 0:>14.2f}%")
    print(f"{'Winning Trades':<25} {num_winning:>15}")
    print(f"{'Losing Trades':<25} {num_losing:>15}")
    print(f"{'Even Trades':<25} {num_even:>15}")
    print("-" * 50)
    print(f"{'Avg. Trade Net Profit':<25} {avg_trade:>15.2f} money")
    print(f"{'Avg. Winning Trade':<25} {avg_win:>15.2f} money")
    print(f"{'Avg. Losing Trade':<25} {avg_loss:>15.2f} money")
    print(f"{'Ratio Avg Win/Avg Loss':<25} {(abs(avg_win/avg_loss) if avg_loss!=0 else 0):>15.3f}")
    print(f"{'Largest Winning Trade':<25} {largest_win:>15.2f} money")
    print(f"{'Largest Losing Trade':<25} {largest_loss:>15.2f} money")
    print(f"{'Largest Win % Gross':<25} {largest_win_pct_gross:>14.2f}%")
    print(f"{'Largest Loss % Gross':<25} {largest_loss_pct_gross:>14.2f}%")
    print("-" * 50)
    print(f"{'Max Consec. Winning':<25} {max_win_streak:>15}")
    print(f"{'Max Consec. Losing':<25} {max_loss_streak:>15}")
    print(f"{'Max Consec. Winning':<25} {max_win_streak:>15} {win_streak_str}")
    print(f"{'Max Consec. Losing':<25} {max_loss_streak:>15} {loss_streak_str}")
    print("-" * 50)

    if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
        try:
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)
        except:
            df['datetime'] = pd.to_datetime(df['timestamp'], utc=True)
    else:
        df['datetime'] = pd.to_datetime(df['timestamp'], utc=True) if df['timestamp'].dt.tz is not None else df['timestamp']
    
    df = df.set_index('datetime')
    equity_col = 'portfolio_equity' if 'portfolio_equity' in df.columns else 'portfolio_balance'
    
    daily_equity: pd.Series = df[equity_col].resample('D').last().ffill()
    daily_returns: pd.Series = daily_equity.pct_change().dropna()
    
    if daily_returns.empty:
        daily_equity = df[equity_col]
        daily_returns = daily_equity.pct_change().dropna()
        if daily_returns.empty:
            return None

    portfolio_variance: float = float(daily_returns.var())
    daily_std_dev: float = float(daily_returns.std())
    two_sigma: float = daily_std_dev * 2
    value_at_risk_5pct: float = float(daily_returns.quantile(0.05))
    
    peak: pd.Series = daily_equity.cummax()
    drawdown: pd.Series = (daily_equity - peak) / peak
    
    max_dd_idx: pd.Timestamp = drawdown.idxmin()
    max_dd_pct: float = float(drawdown.min())
    trough_value: float = float(daily_equity[max_dd_idx])

    peak_val_at_dd: float = float(peak[max_dd_idx])
    
    peak_date: pd.Timestamp = daily_equity[daily_equity == peak_val_at_dd].loc[:max_dd_idx].index[-1]
    
    max_dd_value: float = peak_val_at_dd - trough_value

    decline_duration: pd.Timedelta = max_dd_idx - peak_date

    recovery_subset: pd.Series = daily_equity.loc[max_dd_idx:]
    recovery_date: Optional[pd.Timestamp] = recovery_subset[recovery_subset >= peak_val_at_dd].index.min() if not recovery_subset[recovery_subset >= peak_val_at_dd].empty else None

    net_profit_as_pct_dd: float = (total_net_profit / abs(max_dd_value) * 100) if max_dd_value != 0 else 0.0
    
    recovery_str: str = "Not Recovered"
    if pd.notna(recovery_date):
        days_to_recover: int = (recovery_date - max_dd_idx).days
        recovery_str = f"{days_to_recover} Days (recovered by {recovery_date.date()})"

    print("DRAWDOWN ANALYSIS")
    print("-" * 50)
    print(f"High Water Mark:    {peak_val_at_dd:.2f} money  (on {peak_date.date()})")
    print(f"Low Water Mark:     {trough_value:.2f} money  (on {max_dd_idx.date()})")
    print(f"Drawdown Depth:     {max_dd_value:.2f} money")
    print(f"Drawdown %:         {max_dd_pct*100:.2f}%")
    print(f"Decline Duration:   {decline_duration.days} Days")
    print(f"Recovery Time:      {recovery_str}")
    print(f"{'Net Profit % of DD':<25} {net_profit_as_pct_dd:>14.2f}%")
    print("-" * 50)
    
    metrics_data: Dict[str, Any] = {
        'start_balance': start_balance,
        'end_balance': end_balance,
        'total_return_pct': total_return_pct,
        'total_net_profit': total_net_profit,
        'gross_profit': gross_profit,
        'gross_loss': gross_loss,
        'profit_factor': profit_factor,
        'total_trades': total_trades,
        'num_winning': num_winning,
        'num_losing': num_losing,
        'num_even': num_even,
        'pct_profitable': (num_winning / total_trades * 100) if total_trades > 0 else 0.0,
        'avg_trade_net_profit': avg_trade,
        'avg_winning_trade': avg_win,
        'avg_losing_trade': avg_loss,
        'ratio_avg_win_loss': abs(avg_win / avg_loss) if avg_loss != 0 else 0.0,
        'largest_winning_trade': largest_win,
        'largest_losing_trade': largest_loss,
        'largest_win_pct_gross': largest_win_pct_gross,
        'largest_loss_pct_gross': largest_loss_pct_gross,
        'max_consec_winning': max_win_streak,
        'max_consec_losing': max_loss_streak,
        'daily_return_variance': portfolio_variance,
        'daily_two_sigma_pct': two_sigma * 100,
        'daily_var_5pct': value_at_risk_5pct * 100,
        'high_water_mark': peak_val_at_dd,
        'high_water_mark_date': peak_date,
        'low_water_mark': trough_value,
        'low_water_mark_date': max_dd_idx,
        'drawdown_depth_money': max_dd_value,
        'max_drawdown_pct': max_dd_pct * 100,
        'decline_duration_days': decline_duration.days,
        'recovery_status_str': recovery_str,
        'recovery_date': recovery_date if pd.notna(recovery_date) else None,
        'net_profit_as_pct_dd': net_profit_as_pct_dd
    }

    def clean_metric(val):
        if isinstance(val, (float, np.float64, pd.Series, pd.Timestamp)):
             if hasattr(val, 'item'): val = val.item()
        if isinstance(val, (float, np.float64, np.float32)):
            if math.isnan(val) or math.isinf(val):
                return 0.0
        return val

    metrics_data = {k: clean_metric(v) for k, v in metrics_data.items()}

    return pd.DataFrame([metrics_data])