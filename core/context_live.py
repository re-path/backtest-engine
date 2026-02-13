import json
import redis
import pandas as pd
import os
from typing import List, Dict, Any, Optional
from core.context import Context, Position, StockMath
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ContextLive(Context):
    def __init__(self, initial_balance: float, slippage: float, execution_delay: int = 0, broker_fee: float = 0.0, annual_interest_rate: float = 0.0) -> None:
        # We don't pass event_log because we will manage it in Redis
        # But Context expects it, so we pass an empty list which we won't use directly
        super().__init__(initial_balance, slippage, [], execution_delay, broker_fee, annual_interest_rate)
        
        REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
        REDIS_PORT = int(os.getenv("REDIS_PORT", 6380))
        self.redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        
        # Initialize keys
        self.KEY_BALANCE = "live:balance"
        self.KEY_POSITIONS = "live:positions"
        self.KEY_ORDERS = "live:orders"
        self.KEY_LOG = "live:log"
        self.KEY_STATE = "live:state"
        
        # Initialize balance if not present
        if not self.redis_client.exists(self.KEY_BALANCE):
            self.redis_client.set(self.KEY_BALANCE, initial_balance)
            
        # We don't need local self._positions, self.event_log, self.state, self.pending_orders
        # because we fetch them from Redis on demand or update Redis directly.
        # However, parent methods might access them, so we should be careful.
        # Ideally, we override all methods that access them.

    def get_positions(self) -> Dict[str, Position]:
        raw_positions = self.redis_client.hgetall(self.KEY_POSITIONS)
        positions = {}
        for ticker, data_str in raw_positions.items():
            data = json.loads(data_str)
            positions[ticker] = Position(
                ticker=data['ticker'],
                share_units=data['share_units'],
                entry_price=data['entry_price'],
                time=data['time']
            )
        return positions

    def get_position(self, ticker: str) -> Optional[Position]:
        data_str = self.redis_client.hget(self.KEY_POSITIONS, ticker)
        if data_str:
            data = json.loads(data_str)
            return Position(
                ticker=data['ticker'],
                share_units=data['share_units'],
                entry_price=data['entry_price'],
                time=data['time']
            )
        return None

    def get_balance(self) -> float:
        val = self.redis_client.get(self.KEY_BALANCE)
        return float(val) if val else 0.0

    def set_balance(self, value: float) -> None:
        self.redis_client.set(self.KEY_BALANCE, value)

    def set_state(self, key: str, value: Any) -> None:
        self.redis_client.hset(self.KEY_STATE, key, json.dumps(value))

    def get_state(self, key: str, default: Any = None) -> Any:
        val = self.redis_client.hget(self.KEY_STATE, key)
        if val:
            try:
                return json.loads(val)
            except:
                return val
        return default

    def _execute_buy(self, ticker: str, money_amount: float, current_price: float, current_time: Any) -> float:
        # Pre-calc fee
        fee = money_amount * self.broker_fee
        total_cost = money_amount + fee
        
        balance = self.get_balance()
        
        if balance < total_cost:
            return 0.0
        
        actual_buy_price = current_price * (1 + self.slippage)
        fee = money_amount * self.broker_fee
        total_cost = money_amount + fee
        
        share_units = StockMath.calculate_share_units_from_money(money_invest=money_amount, entry_price=actual_buy_price)
        
        if share_units > 0 and balance >= total_cost:
            # Update balance
            new_balance = balance - total_cost
            self.set_balance(new_balance)
            
            # Update position
            pos_data_str = self.redis_client.hget(self.KEY_POSITIONS, ticker)
            if pos_data_str:
                pos_data = json.loads(pos_data_str)
                pos_data['share_units'] += share_units
                # Should we average entry price? Context doesn't seem to do it explicitly for existing Position class, 
                # but Position class is simple. 
                # Original Context logic:
                # self._positions[ticker].share_units += share_units
                # It just updates share units, keeping original entry price? 
                # Checking Context.py: yes, it just adds share_units. Entry price remains of the first entry? 
                # Line 120: self._positions[ticker].share_units += share_units
                # So we do the same.
            else:
                pos_data = {
                    'ticker': ticker,
                    'share_units': share_units,
                    'entry_price': actual_buy_price,
                    'time': str(current_time) # Serialize time
                }
            
            self.redis_client.hset(self.KEY_POSITIONS, ticker, json.dumps(pos_data))
            
            # Log
            self._log(current_time, "BUY", ticker, actual_buy_price, -total_cost)
            
            return share_units
        
        return 0.0

    def _execute_buy_shares(self, ticker: str, share_count: float, current_price: float, current_time: Any) -> float:
        actual_buy_price = current_price * (1 + self.slippage)
        base_cost = share_count * actual_buy_price
        fee = base_cost * self.broker_fee
        total_cost = base_cost + fee
        
        balance = self.get_balance()
        
        if balance >= total_cost:
            new_balance = balance - total_cost
            self.set_balance(new_balance)
            
            pos_data_str = self.redis_client.hget(self.KEY_POSITIONS, ticker)
            if pos_data_str:
                pos_data = json.loads(pos_data_str)
                pos_data['share_units'] += share_count
            else:
                pos_data = {
                    'ticker': ticker,
                    'share_units': share_count,
                    'entry_price': actual_buy_price,
                    'time': str(current_time)
                }
            
            self.redis_client.hset(self.KEY_POSITIONS, ticker, json.dumps(pos_data))
            self._log(current_time, "BUY", ticker, actual_buy_price, -total_cost)
            return share_count
            
        return 0.0

    def _execute_sell(self, ticker: str, share_units_amount: float, current_price: float, current_time: Any, reason: str) -> float:
        pos_data_str = self.redis_client.hget(self.KEY_POSITIONS, ticker)
        if not pos_data_str:
            return 0.0
            
        pos_data = json.loads(pos_data_str)
        current_shares = pos_data['share_units']
        
        if share_units_amount > current_shares:
            share_units_amount = current_shares
            
        actual_sell_price = current_price * (1 - self.slippage)
        money_received = StockMath.calculate_money_from_share_units(share_units_to_sell=share_units_amount, exit_price=actual_sell_price)
        
        fee = money_received * self.broker_fee
        net_money = money_received - fee
        
        # Update balance
        balance = self.get_balance()
        self.set_balance(balance + net_money)
        
        # Update position
        pos_data['share_units'] -= share_units_amount
        
        if pos_data['share_units'] <= 1e-9:
            self.redis_client.hdel(self.KEY_POSITIONS, ticker)
        else:
            self.redis_client.hset(self.KEY_POSITIONS, ticker, json.dumps(pos_data))
            
        self._log(current_time, reason, ticker, actual_sell_price, net_money)
        
        return net_money

    def _log(self, timestamp: Any, event_type: str, ticker: str, price: float, money_change: float) -> None:
        log_entry = {
            "timestamp": str(timestamp),
            "event_type": event_type,
            "ticker": ticker,
            "price": price,
            "money_change": money_change,
            "portfolio_balance": self.get_balance()
        }
        self.redis_client.rpush(self.KEY_LOG, json.dumps(log_entry))

    # Pending Orders Logic
    # We override methods that add/check pending orders
    
    def buy(self, ticker: str, money_amount: float, current_price: float, current_time: Any) -> float:
        if self.execution_delay == 0:
            return self._execute_buy(ticker, money_amount, current_price, current_time)
        
        # Check if pending
        orders = self._get_pending_orders()
        for order in orders:
            if order['ticker'] == ticker and order['type'] == 'BUY':
                return 0.0

        new_order = {
            'type': 'BUY',
            'ticker': ticker,
            'amount': money_amount,
            'trigger_time': str(current_time)
        }
        self.redis_client.rpush(self.KEY_ORDERS, json.dumps(new_order))
        return 0.0 

    def sell(self, ticker: str, share_units_amount: float, current_price: float, current_time: Any, reason: str = "SELL") -> float:
        if self.execution_delay == 0:
            return self._execute_sell(ticker, share_units_amount, current_price, current_time, reason)
        
        if reason in ['STOP', 'LIQUIDATE', 'CLOSE']:
            orders = self._get_pending_orders()
            for order in orders:
                if order['ticker'] == ticker and order['type'] == 'SELL' and order['reason'] in ['STOP', 'LIQUIDATE', 'CLOSE']:
                    return 0.0 
        
        new_order = {
            'type': 'SELL',
            'ticker': ticker,
            'amount': share_units_amount,
            'trigger_time': str(current_time),
            'reason': reason
        }
        self.redis_client.rpush(self.KEY_ORDERS, json.dumps(new_order))
        return 0.0

    def buy_protected(self, ticker: str, share_count: float, current_price: float, current_time: Any) -> float:
        if share_count < 10 or share_count % 10 != 0:
            return 0.0

        if self.execution_delay == 0:
            return self._execute_buy_shares(ticker, share_count, current_price, current_time)
        
        orders = self._get_pending_orders()
        for order in orders:
            if order['ticker'] == ticker and order['type'] == 'BUY_SHARES':
                return 0.0

        new_order = {
            'type': 'BUY_SHARES',
            'ticker': ticker,
            'amount': share_count,
            'trigger_time': str(current_time)
        }
        self.redis_client.rpush(self.KEY_ORDERS, json.dumps(new_order))
        return 0.0

    def process_pending_orders(self, current_ticker: str, current_price: float, current_time: Any) -> None:
        orders = self._get_pending_orders()
        if not orders:
            return

        remaining_orders = []
        
        # We need to handle time comparison. 'trigger_time' is string in Redis.
        # current_time might be datetime or pd.Timestamp.
        # We assume isoformat string or similar.
        
        import pandas as pd
        
        for order in orders:
            if order['ticker'] == current_ticker:
                # Parse trigger_time
                trigger_time = pd.Timestamp(order['trigger_time'])
                
                # Check delay
                try:
                    time_diff = (current_time - trigger_time).total_seconds()
                except:
                    # Fallback if types mismatch heavily
                    time_diff = 0
                
                if time_diff >= self.execution_delay:
                    if order['type'] == 'BUY':
                        self._execute_buy(order['ticker'], order['amount'], current_price, current_time)
                    elif order['type'] == 'BUY_SHARES':
                        self._execute_buy_shares(order['ticker'], order['amount'], current_price, current_time)
                    elif order['type'] == 'SELL':
                        self._execute_sell(order['ticker'], order['amount'], current_price, current_time, order['reason'])
                    continue
            
            remaining_orders.append(order)
            
        # Update Redis with remaining orders
        # Since this modifies the whole list, we can DEL and RPUSH
        # But race conditions? Single threaded usage assumed or we need locking.
        # Given "live" usage, we might be the only writer to orders? 
        # Or better functionality:
        # We can't atomically update list like this easily without Lua or WATCH.
        # For now, simplistic approach: delete key, push remaining.
        
        self.redis_client.delete(self.KEY_ORDERS)
        for order in remaining_orders:
            self.redis_client.rpush(self.KEY_ORDERS, json.dumps(order))

    def _get_pending_orders(self) -> List[Dict[str, Any]]:
        raw_list = self.redis_client.lrange(self.KEY_ORDERS, 0, -1)
        return [json.loads(x) for x in raw_list]
