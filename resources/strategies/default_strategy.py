class Strategy:
    def __init__(self, **kwargs):
        # Strategy parameters are passed to __init__
        self.params = kwargs
        self.ema_period = kwargs.get('ema_period', 20)
        self.k = 2 / (self.ema_period + 1)

    def on_bar(self, context, bar):
        """
        Main Strategy Logic with EMA Example
        """
        
        # 1. EMA Calculation Example
        # Use context.get() / context.set() to maintain indicator state across bars
        emas = context.get('emas', {})
        prev_ema = emas.get(bar.ticker, bar.price)
        
        # Calculate new EMA for this bar
        current_ema = (bar.price * self.k) + (prev_ema * (1 - self.k))
        
        # Save updated EMAs back to context state
        emas[bar.ticker] = current_ema
        context.set('emas', emas)
        
        # 2. CUSTOM METRIC (Visualized in Ticker Chart)
        # context.set_metric(name, timestamp, ticker, value)
        # This will automatically show up as a "Local Overlay" in the chart legend.
        context.set_metric("EMA_Example", bar.timestamp, bar.ticker, current_ema)
        
        # 3. TRADING LOGIC
        # Buy if price is more than 5% below EMA
        if bar.price < current_ema * 0.95:
             # Invest 20% of current balance
             invest_amount = context.get_balance() * 0.20
             context.buy(bar.ticker, invest_amount, bar.price, bar.timestamp)
             
        # Sell/Exit if price is more than 5% above EMA
        elif bar.price > current_ema * 1.05:
             # Close entire position for this ticker
             context.close(bar.ticker, bar.price, bar.timestamp, "MeanRev_Exit")
