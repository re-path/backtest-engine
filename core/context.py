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
    def __init__(self, initial_balance: float, slippage: float, event_log: List[Dict[str, Any]], execution_delay: int = 0) -> None:
        self.balance: float = initial_balance
        self.slippage: float = slippage
        self.positions: Dict[str, Position] = {}
        self.event_log: List[Dict[str, Any]] = event_log
        self.state: Dict[str, Any] = {}
        self.traded_tickers: Set[str] = set()
        
        self.execution_delay: int = execution_delay
        self.pending_orders: List[Dict[str, Any]] = [] 

    def set_state(self, key: str, value: Any) -> None:
        self.state[key] = value

    def get_state(self, key: str, default: Any = None) -> Any:
        return self.state.get(key, default)

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
        if self.balance < money_amount:
            return 0.0
        
        actual_buy_price: float = current_price * (1 + self.slippage)
        share_units: float = StockMath.calculate_share_units_from_money(money_invest=money_amount, entry_price=actual_buy_price)
        
        if share_units > 0:
            self.balance -= money_amount
            if ticker not in self.positions:
                self.positions[ticker] = Position(ticker, share_units, actual_buy_price, current_time)
            else:
                self.positions[ticker].share_units += share_units
            
            self.traded_tickers.add(ticker)
            self._log(current_time, "BUY", ticker, actual_buy_price, -money_amount)
        
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

    def _execute_sell(self, ticker: str, share_units_amount: float, current_price: float, current_time: Any, reason: str) -> float:
        if ticker not in self.positions:
            return 0.0
        
        pos: Position = self.positions[ticker]
        if share_units_amount > pos.share_units:
            share_units_amount = pos.share_units
            
        actual_sell_price: float = current_price * (1 - self.slippage)
        money_received: float = StockMath.calculate_money_from_share_units(share_units_to_sell=share_units_amount, exit_price=actual_sell_price)
        
        self.balance += money_received
        pos.share_units -= share_units_amount
        
        self._log(current_time, reason, ticker, actual_sell_price, money_received)
        
        if pos.share_units <= 1e-9:
            del self.positions[ticker]
            
        return money_received

    def close(self, ticker: str, current_price: float, current_time: Any, reason: str = "CLOSE") -> float:
        if ticker in self.positions:
            return self.sell(ticker, self.positions[ticker].share_units, current_price, current_time, reason)
        return 0.0

    def _log(self, timestamp: Any, event_type: str, ticker: str, price: float, money_change: float) -> None:
        self.event_log.append({
            "timestamp": timestamp,
            "event_type": event_type,
            "ticker": ticker,
            "price": price,
            "money_change": money_change,
            "portfolio_balance": self.balance
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
                    elif order['type'] == 'SELL':
                        amount: float = order['amount']
                        self._execute_sell(order['ticker'], amount, current_price, current_time, order['reason'])
                    
                    continue
            
            remaining_orders.append(order)
        
        self.pending_orders = remaining_orders
