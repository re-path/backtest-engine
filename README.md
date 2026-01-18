# Backtest Engine

A comprehensive, event-driven backtesting engine for trading strategies, built with Python. This project allows users to define custom strategies, simulate trading against historical data, and analyze performance with detailed metrics and interactive visualizations.

## Features

- **Event-Driven Architecture:** Simulates trading bar-by-bar to realistically model market conditions and order execution.
- **Custom Strategy Support:** Easily define strategies by implementing an `on_bar` method.
- **Robust Context Management:** Manages portfolio state, positions, and order execution including slippage and delays.
- **Detailed Analysis:** Generates comprehensive performance metrics (Sharpe, Drawdown, Win/Loss ratio, etc.).
- **Interactive Visualizations:** Uses Plotly to create interactive charts of trade entries/exits and portfolio equity curves.
- **FastAPI Integration:** Includes a REST API to run backtests remotely.

## Project Structure

- `core/`: Contains the core logic of the engine.
    - `engine.py`: The main event loop driving the backtest.
    - `context.py`: Manages account balance, positions, and orders.
    - `analysis.py`: Calculates performance metrics and generates plots.
    - `api.py`: FastAPI endpoints for interacting with the engine.
- `main.py`: Entry point to run the API server.
- `ui/`: (Optional) Frontend assets.

## Installation

Ensure you have Python 3.13 or higher installed.

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd backtest-engine
    ```

2.  **Install dependencies:**
    This project uses `uv` for dependency management, but you can also use `pip`.

    **Using uv (Recommended):**
    ```bash
    uv sync
    ```

    **Using pip:**
    ```bash
    pip install -e .
    ```

## Usage

### Running the API Server

Start the FastAPI server to expose the backtesting endpoint:

```bash
python main.py
```

The server will start on `http://0.0.0.0:8000`.

### Running a Backtest

You can trigger a backtest by sending a POST request to `/run-backtest`.

**Example Request:**

```json
POST /run-backtest
{
    "start_date": "2024-01-01",
    "end_date": "2024-06-01",
    "initial_balance": 10000.0,
    "slippage": 0.001,
    "strategy_params": {}
}
```

The response will include performance metrics, a summary of trades, and a JSON object for the Plotly chart.

### Developing a Strategy

To create a new strategy, define a class with an `on_bar` method. This method is called for every time step (bar) in the simulation.

```python
class MyStrategy:
    def __init__(self, **kwargs):
        # Initialize strategy parameters
        self.params = kwargs

    def on_bar(self, context, bar):
        # bar.ticker, bar.price, bar.timestamp are available
        
        # Example: Simple Buy and Hold
        if context.balance > 0:
            context.buy(bar.ticker, context.balance, bar.price, bar.timestamp)

        # Using Context:
        # context.buy(ticker, amount, price, time)
        # context.sell(ticker, amount, price, time)
        # context.close(ticker, price, time)
        # context.set_state(key, value) / context.get_state(key, default)
```

## Core Modules

### Engine (`core/engine.py`)
Iterates through data chunks and feeds bars to the strategy. Handles the main loop and progress tracking.

### Context (`core/context.py`)
The `Context` object is passed to your strategy's `on_bar` method. It acts as your interface to the market:
- **`buy()`**: Place a buy order.
- **`sell()`**: Place a sell order.
- **`close()`**: Close a position for a specific ticker.
- **`get_state()` / `set_state()`**: Persist custom variables across bars (e.g., indicators, flags).

### Analysis (`core/analysis.py`)
Produces a detailed DataFrame of metrics, including:
- Total Return & Net Profit
- Win Rate & Profit Factor
- Max Drawdown & Recovery Time
- Sharpe Ratio inputs (Annualized Volatility, etc.)