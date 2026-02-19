import pytest
from playwright.sync_api import Page, expect
import subprocess
import time
import os
import signal
import re

# --- REUSABLE FIXTURES ---

@pytest.fixture(scope="module")
def playwright_context(browser):
    context = browser.new_context()
    yield context
    context.close()

@pytest.fixture(scope="module")
def page(playwright_context):
    return playwright_context.new_page()

@pytest.fixture(scope="module", autouse=True)
def dev_server():
    # Start the server on a unique port for regression testing
    port = "1220"
    env = os.environ.copy()
    env["API_PORT"] = port
    env["REDIS_PORT"] = "6381"
    env["MARIMO_PORT"] = "2719"
    env["INITIAL_BALANCE"] = "10000"
    
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    
    process = subprocess.Popen(
        ["uv", "run", "python", "main.py"],
        env=env,
        preexec_fn=os.setsid,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for server to start
    time.sleep(15) 
    
    yield f"http://localhost:{port}"
    
    # Cleanup
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except ProcessLookupError:
        pass

# --- REGRESSION TESTS ---

def test_01_strategy_tab_functionality(page: Page, dev_server):
    page.goto(f"{dev_server}/ui/index.html")
    
    # Check Header
    expect(page.get_by_text("BacktestEngine", exact=False)).to_be_visible()
    
    # Verify Strategy Tab is active by default
    expect(page.get_by_text("CONFIGURATION", exact=False)).to_be_visible()
    
    # Test Strategy Name Edit
    strat_input = page.locator("input[value='My Strategy']")
    strat_input.fill("Regression Test Strategy")
    expect(page.locator("input[value='Regression Test Strategy']")).to_be_visible()

    # Verify Parameters are editable
    balance_input = page.locator("input[name='initial_balance']")
    balance_input.fill("50000")
    expect(balance_input).to_have_value("50000")

def test_02_backtest_execution_and_results(page: Page, dev_server):
    page.goto(f"{dev_server}/ui/index.html")
    
    # Run Backtest
    run_btn = page.get_by_text("RUN STRATEGY", exact=False)
    run_btn.click()
    
    # Wait for Results Tab - using role and more specific selector to avoid strict mode violations
    expect(page.get_by_role("button", name=re.compile("^Trades$", re.IGNORECASE))).to_be_visible(timeout=180000)
    
    # Verify Chart is rendered
    chart_container = page.locator("#chart-container-full")
    expect(chart_container).to_be_visible()
    
    # Switch to Trades Sub-tab
    page.get_by_role("button", name=re.compile("^Trades$", re.IGNORECASE)).click()
    expect(page.locator("table")).to_be_visible()
    expect(page.get_by_role("columnheader", name="Event")).to_be_visible()

def test_03_performance_metrics_accuracy(page: Page, dev_server):
    page.goto(f"{dev_server}/ui/index.html")
    
    # Run backtest
    page.get_by_text("RUN STRATEGY", exact=False).click()
    expect(page.get_by_role("button", name=re.compile("^Trades$", re.IGNORECASE))).to_be_visible(timeout=180000)
    
    # Go to Performance Tab
    page.get_by_text("PERFORMANCE", exact=False).click()
    
    # Verify metrics
    expect(page.get_by_text("Trade Statistics", exact=False)).to_be_visible()
    expect(page.get_by_text("Drawdown & Risk", exact=False)).to_be_visible()
    expect(page.get_by_text("Profit Factor", exact=False)).to_be_visible()
    expect(page.get_by_text("Max Drawdown %", exact=False)).to_be_visible()

def test_04_optimize_tab_fix_verification(page: Page, dev_server):
    page.goto(f"{dev_server}/ui/index.html")
    
    # Go to OPTIMIZE Tab
    page.get_by_text("OPTIMIZE", exact=False).click()
    
    # Verify OptimizationPanel
    expect(page.get_by_text("Optimization Configuration", exact=False)).to_be_visible()
    expect(page.get_by_text("START OPTIMIZATION", exact=False)).to_be_visible()

def test_05_tools_and_ml_tabs(page: Page, dev_server):
    page.goto(f"{dev_server}/ui/index.html")
    
    # Manual Analysis
    page.get_by_text("MANUAL ANALYSIS", exact=False).click()
    expect(page.get_by_role("heading", name=re.compile("Manual Analysis", re.IGNORECASE))).to_be_visible()
    
    # SQL Snippets
    page.get_by_text("SQL SNIPPETS", exact=False).click()
    expect(page.get_by_role("heading", name=re.compile("Categories", re.IGNORECASE))).to_be_visible()
    
    # ML Studio
    page.get_by_text("ML STUDIO", exact=False).click()
    expect(page.get_by_text("START TRAINING", exact=False)).to_be_visible()
