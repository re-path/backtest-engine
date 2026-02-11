class Strategy:
    def __init__(self, **kwargs):
        # Strategy parameters are passed to __init__
        self.params = kwargs

    def on_bar(self, context, bar):
        """
        Main Strategy Logic
        
        API Documentation:
        ------------------
        Accessing Data:
          bar.price       (float) : Current close price of the asset
          bar.timestamp   (params): Current timestamp (pandas Timestamp)
          bar.ticker      (str)   : Ticker symbol
          
        Context (State & Actions):
          context.get_balance()           : Current available cash (Affected by fees & interest)
          context.get_positions()         : Dictionary of active positions {ticker: Position}
          
          # NOTE: Broker fees and Interest rates are configured in the right panel
          # and applied automatically by the engine.
          
          # STATE MANAGEMENT (CRITICAL):
          # Do NOT use self.variable = x. Use context.get/set instead.
          context.set(key, value)         : Store a value
          context.get(key, default=None)  : Retrieve a value, returns default if not found
          
          # TRADING ACTIONS:
          context.buy(ticker, money_amount, price, time)
          context.buy_protected(ticker, share_count, price, time) # Shares (10, 20, 30...)
          context.sell(ticker, share_fraction, price, time, reason="SELL")
          context.close(ticker, price, time, reason="CLOSE") # Close entire position
          
        """
        
        # Example 1: Use context.get() to manage state
        # Let's count how many bars we've seen for this ticker
        ticker_count_key = f"{bar.ticker}_count"
        current_count = context.get(ticker_count_key, 0)
        context.set(ticker_count_key, current_count + 1)
        
        # Example 2: Accessing Parameters
        buy_probability = self.params.get('buy_prob', 0.10) 
        
        # Example 3: Trading Logic (Protected)
        # buy_protected requires share counts in multiples of 10
        import random
        if random.random() < buy_probability:
             # Buy 10 shares if we have enough balance
             # This automatically calculates and deducts the cash required.
             context.buy_protected(bar.ticker, 10, bar.price, bar.timestamp)
        
        # Example 4: Risk Management
        positions = context.get_positions()
        if bar.ticker in positions:
             pos = positions[bar.ticker]
             # Check for 5% profit
             if bar.price > pos.entry_price * 1.05:
                  context.sell(bar.ticker, pos.share_units, bar.price, bar.timestamp, "SELL")
