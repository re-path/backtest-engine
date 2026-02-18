# core/context.py
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

class Position:
    def __init__(self, ticker: str, share_units: float, entry_price: float, time: Any) -> None:
        self.ticker: str = ticker
        self.share_units: float = share_units
        self.entry_price: float = entry_price
        self.time: Any = time

class PriceMath:
    @staticmethod
    def calculate_quantity_from_cash(cash_invested: float, price: float) -> float:
        if cash_invested <= 0 or price <= 0:
            return 0.0
        return cash_invested / price

    @staticmethod
    def calculate_cash_from_quantity(quantity: float, price: float) -> float:
        if quantity <= 0 or price <= 0:
            return 0.0
        return quantity * price

    @staticmethod
    def calculate_share_units_from_money(money_invest: float, entry_price: float) -> float:
        return PriceMath.calculate_quantity_from_cash(money_invest, entry_price)

    @staticmethod
    def calculate_money_from_share_units(share_units_to_sell: float, exit_price: float) -> float:
        return PriceMath.calculate_cash_from_quantity(share_units_to_sell, exit_price)

StockMath = PriceMath

class Context:
    def __init__(self, initial_balance: float, slippage: float, event_log: List[Dict[str, Any]], execution_delay: int = 0, broker_fee: float = 0.0, annual_interest_rate: float = 0.0) -> None:
        self._balance: float = initial_balance
        self.slippage: float = slippage
        self.broker_fee: float = broker_fee
        self.annual_interest_rate: float = annual_interest_rate
        
        self._positions: Dict[str, Position] = {}
        self.event_log: List[Dict[str, Any]] = event_log
        self.state: Dict[str, Any] = {}
        self.traded_tickers: Set[str] = set()
        
        self.execution_delay: int = execution_delay
        self.pending_orders: List[Dict[str, Any]] = [] 
        
        # Structure: { ticker: { metric_name: [ { 'timestamp': ts, 'value': val }, ... ] } }
        self.custom_metrics: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

    def set_metric(self, ticker: str, timestamp: Any, metric_name: str, metric_value: Any) -> None:
        """
        Record a custom metric for a specific ticker and timestamp.
        Used for plotting indicators or strategy-specific values in the UI.
        """
        if ticker not in self.custom_metrics:
            self.custom_metrics[ticker] = {}
        
        if metric_name not in self.custom_metrics[ticker]:
            self.custom_metrics[ticker][metric_name] = []
            
        self.custom_metrics[ticker][metric_name].append({
            'timestamp': timestamp,
            'value': metric_value
        })

    def set_state(self, key: str, value: Any) -> None:
        self.state[key] = value

    def get_state(self, key: str, default: Any = None) -> Any:
        return self.state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Alias for set_state"""
        self.set_state(key, value)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Alias for get_state"""
        return self.get_state(key, default)
    
    def get_positions(self) -> Dict[str, Position]:
        return self._positions

    def get_balance(self) -> float:
        return self._balance

    def get_position(self, ticker: str) -> Optional[Position]:
        return self._positions.get(ticker)

    def buy(self, ticker: str, money_amount: float, current_price: float, current_time: Any) -> float:
        if self.execution_delay == 0:
            return self._execute_buy(ticker, money_amount, current_price, current_time)
        
        for order in self.pending_orders:
            if order['ticker'] == ticker and order['type'] == 'BUY':
                return 0.0

        self.pending_orders.append({
            'type': 'BUY',
            'ticker': ticker,
            'amount': money_amount,
            'trigger_time': current_time
        })
        return 0.0 

    def _execute_buy(self, ticker: str, money_amount: float, current_price: float, current_time: Any) -> float:
        # Pre-calc fee to check if we have enough balance
        fee = money_amount * self.broker_fee
        total_cost = money_amount + fee
        
        if self._balance < total_cost:
            return 0.0
        
        actual_buy_price: float = current_price * (1 + self.slippage)
        # Fee is calculated on the transaction amount (money_amount)
        fee: float = money_amount * self.broker_fee
        total_cost: float = money_amount + fee
        
        share_units: float = StockMath.calculate_share_units_from_money(money_invest=money_amount, entry_price=actual_buy_price)
        
        if share_units > 0 and self._balance >= total_cost:
            self._balance -= total_cost
            if ticker not in self._positions:
                self._positions[ticker] = Position(ticker, share_units, actual_buy_price, current_time)
            else:
                self._positions[ticker].share_units += share_units
            
            self.traded_tickers.add(ticker)
            self._log(current_time, "BUY", ticker, actual_buy_price, -total_cost)
        
        return share_units

    def sell(self, ticker: str, share_units_amount: float, current_price: float, current_time: Any, reason: str = "SELL") -> float:
        if self.execution_delay == 0:
            return self._execute_sell(ticker, share_units_amount, current_price, current_time, reason)
        
        if reason in ['STOP', 'LIQUIDATE', 'CLOSE']:
            for order in self.pending_orders:
                if order['ticker'] == ticker and order['type'] == 'SELL' and order['reason'] in ['STOP', 'LIQUIDATE', 'CLOSE']:
                    return 0.0 
        
        self.pending_orders.append({
            'type': 'SELL',
            'ticker': ticker,
            'amount': share_units_amount,
            'trigger_time': current_time,
            'reason': reason
        })
        return 0.0

    def buy_protected(self, ticker: str, share_count: float, current_price: float, current_time: Any) -> float:
        """
        Enforces buying in multiples of 10, with a minimum of 10.
        Calculates required cash automatically.
        """
        if share_count < 10 or share_count % 10 != 0:
            return 0.0

        if self.execution_delay == 0:
            return self._execute_buy_shares(ticker, share_count, current_price, current_time)
        
        # Check if already pending for this ticker/type
        for order in self.pending_orders:
            if order['ticker'] == ticker and order['type'] == 'BUY_SHARES':
                return 0.0

        self.pending_orders.append({
            'type': 'BUY_SHARES',
            'ticker': ticker,
            'amount': share_count,
            'trigger_time': current_time
        })
        return 0.0

    def _execute_buy_shares(self, ticker: str, share_count: float, current_price: float, current_time: Any) -> float:
        actual_buy_price: float = current_price * (1 + self.slippage)
        base_cost: float = share_count * actual_buy_price
        fee: float = base_cost * self.broker_fee
        total_cost: float = base_cost + fee
        
        if self._balance >= total_cost:
            self._balance -= total_cost
            if ticker not in self._positions:
                self._positions[ticker] = Position(ticker, share_count, actual_buy_price, current_time)
            else:
                self._positions[ticker].share_units += share_count
            
            self.traded_tickers.add(ticker)
            self._log(current_time, "BUY", ticker, actual_buy_price, -total_cost)
            return share_count
        
        return 0.0

    def _execute_sell(self, ticker: str, share_units_amount: float, current_price: float, current_time: Any, reason: str) -> float:
        if ticker not in self._positions:
            return 0.0
        
        pos: Position = self._positions[ticker]
        if share_units_amount > pos.share_units:
            share_units_amount = pos.share_units
            
        actual_sell_price: float = current_price * (1 - self.slippage)
        money_received: float = StockMath.calculate_money_from_share_units(share_units_to_sell=share_units_amount, exit_price=actual_sell_price)
        
        fee: float = money_received * self.broker_fee
        net_money: float = money_received - fee
        
        self._balance += net_money
        pos.share_units -= share_units_amount
        
        self._log(current_time, reason, ticker, actual_sell_price, net_money)
        
        if pos.share_units <= 1e-9:
            del self._positions[ticker]
            
        return net_money

    def close(self, ticker: str, current_price: float, current_time: Any, reason: str = "CLOSE") -> float:
        if ticker in self._positions:
            return self.sell(ticker, self._positions[ticker].share_units, current_price, current_time, reason)
        return 0.0

    def _log(self, timestamp: Any, event_type: str, ticker: str, price: float, money_change: float) -> None:
        self.event_log.append({
            "timestamp": timestamp,
            "event_type": event_type,
            "ticker": ticker,
            "price": price,
            "money_change": money_change,
            "portfolio_balance": self._balance
        })

    def process_pending_orders(self, current_ticker: str, current_price: float, current_time: Any) -> None:
        if not self.pending_orders:
            return

        remaining_orders: List[Dict[str, Any]] = []
        
        for order in self.pending_orders:
            if order['ticker'] == current_ticker:
                if (current_time - order['trigger_time']).total_seconds() >= self.execution_delay:
                    
                    if order['type'] == 'BUY':
                        self._execute_buy(order['ticker'], order['amount'], current_price, current_time)
                    elif order['type'] == 'BUY_SHARES':
                        self._execute_buy_shares(order['ticker'], order['amount'], current_price, current_time)
                    elif order['type'] == 'SELL':
                        amount: float = order['amount']
                        self._execute_sell(order['ticker'], amount, current_price, current_time, order['reason'])
                    
                    continue
            
            remaining_orders.append(order)
        
        self.pending_orders = remaining_orders

    def load_model(self, model_name: str) -> Any:
        """
        Loads a trained model (or any pickled object) from the data/ directory.
        """
        import pickle
        import os
        
        # Security: prevent directory traversal
        model_name = os.path.basename(model_name)
        
        base_path = "data"
        possible_paths = [
            os.path.join(base_path, model_name),
            os.path.join(base_path, f"{model_name}.pkl"),
            os.path.join(base_path, f"{model_name}.joblib"),
            os.path.join(base_path, f"{model_name}.h5"), # for Keras/LSTM if saved that way
        ]
        
        target_path = None
        for p in possible_paths:
            if os.path.exists(p):
                target_path = p
                break
        
        if not target_path:
            # Check if it's a directory (e.g. for some model formats)
            if os.path.isdir(os.path.join(base_path, model_name)):
                # Just return the path, the user might know how to load it (e.g. keras.models.load_model)
                return os.path.join(base_path, model_name)
            raise FileNotFoundError(f"Model {model_name} not found in {base_path}")
            
        # If it's a file, try to unpickle it
        try:
            with open(target_path, 'rb') as f:
                return pickle.load(f)
        except Exception:
            # If pickle fails, maybe it's a different format (like joblib or h5)
            # For now, return the path and let the strategy handle special loading if needed
            return target_path

