import pytest
from playwright.sync_api import Page, expect
import subprocess
import time
import os
import signal
import re

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
    # Start the server in the background
    # We use 'uv run python main.py'
    # We should probably set a different port to avoid conflicts, but for now we follow main.py defaults
    env = os.environ.copy()
    env["API_PORT"] = "1219" # Use a different port for testing
    
    # We need to make sure we are not starting redis/marimo unnecessarily or they don't conflict
    # Actually main.py starts them. Let's just run it.
    process = subprocess.Popen(
        ["uv", "run", "python", "main.py"],
        env=env,
        preexec_fn=os.setsid
    )
    
    # Wait for server to start
    time.sleep(10) # Give it enough time to start and for marimo/redis to fail or start
    
    yield
    
    # Cleanup: kill the process group
    os.killpg(os.getpgid(process.pid), signal.SIGTERM)

def test_drawdown_and_metrics_display(page: Page):
    # Connect to the test server
    page.goto("http://localhost:1219/ui/index.html")
    
    # 1. Run Strategy
    run_btn = page.get_by_text("RUN STRATEGY")
    expect(run_btn).to_be_visible()
    run_btn.click()
    
    # 2. Wait for loading to complete (RUN STRATEGY button should be enabled again)
    # The button text might change or have a spinner, let's wait for results tab to be active
    # Results tab is auto-switched on success
    expect(page.get_by_role("button", name=re.compile("^Trades$", re.IGNORECASE))).to_be_visible(timeout=180000)
    
    # 3. Go to PERFORMANCE tab
    page.get_by_text("PERFORMANCE").click()
    
    # 4. Verify Metrics
    # Check for Drawdown related metrics
    expect(page.get_by_text("Max Drawdown %")).to_be_visible()
    expect(page.get_by_text("High Water Mark")).to_be_visible()
    expect(page.get_by_text("Net Profit % of DD")).to_be_visible()
    expect(page.get_by_text("Win/Loss Ratio")).to_be_visible()
    
    # Check that values are not "0.00%" or "0.00" if the default strategy makes trades
    # The default strategy typically does some trades.
    # Let's just check that they are rendered as numbers
    dd_val = page.locator("div:has-text('Max Drawdown %') + div").first # This depends on HTML structure
    # Actually AnalysisRow uses label and value. Let's find by text.
    
    # Check for specific metric values if possible, or just non-empty
    expect(page.get_by_text("Total Net Profit")).to_be_visible()
    expect(page.get_by_text("Gross Profit")).to_be_visible()
