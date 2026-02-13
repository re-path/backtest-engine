import uvicorn
from core.api import *
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

app.mount("/ui", StaticFiles(directory="ui"), name="ui")
app.mount("/resources", StaticFiles(directory="resources"), name="resources")

@app.middleware("http")
async def add_no_cache_header(request, call_next):
    # If the request is for UI assets, trick the server into thinking 
    # the browser has NO cached version by stripping validation headers.
    if request.url.path.startswith("/ui"):
        # Modify the scope headers (bytes)
        new_headers = [
            (k, v) for k, v in request.scope["headers"]
            if k.lower() not in (b"if-none-match", b"if-modified-since")
        ]
        request.scope["headers"] = new_headers

    response = await call_next(request)
    
    if request.url.path.startswith("/ui"):
        # Force the browser to never cache and never trust what it has
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        # Strip ETags so the browser can't even try to validate next time
        if "ETag" in response.headers:
            del response.headers["ETag"]
        if "Last-Modified" in response.headers:
            del response.headers["Last-Modified"]
    return response

@app.get("/")
async def root():
    return RedirectResponse(url="/ui/index.html")


if __name__ == "__main__":
    import os
    import uvicorn
    import subprocess
    import atexit
    import signal
    import time
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    # Environment Configurations
    MARIMO_PORT = int(os.getenv("MARIMO_PORT", 2718))
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6380))
    API_PORT = int(os.getenv("API_PORT", 1218))
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    NOTEBOOKS_DIR = os.getenv("NOTEBOOKS_DIR", "resources/notebooks")
    DATA_DIR = os.getenv("DATA_DIR", "data")
    
    # Ensure directories exist
    os.makedirs(NOTEBOOKS_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
        

    def run_marimo(retry=True):
        print(f"Starting Marimo server on port {MARIMO_PORT}...")
        cmd = [
            "uv", "run", "marimo", "edit", 
            "--port", str(MARIMO_PORT), 
            "--headless", 
            "--no-token",
            NOTEBOOKS_DIR
        ]
        # Log to file in data/ for debugging
        log_path = os.path.join(DATA_DIR, "marimo.log")
        log_file = open(log_path, "w+")
        process = subprocess.Popen(cmd, stdout=log_file, stderr=log_file)
        
        # Check if it failed immediately
        time.sleep(2)
        if process.poll() is not None:
            # It died. Check why.
            log_file.seek(0)
            output = log_file.read()
            print(f"Marimo failed to start. Output:\n{output[-500:]}")
            
            if "address already in use" in output or "Address already in use" in output:
                if retry:
                    print(f"Port {MARIMO_PORT} in use. Attempting to kill existing process...")
                    try:
                        subprocess.run(["fuser", "-k", f"{MARIMO_PORT}/tcp"], check=False)
                        time.sleep(1) # Wait for release
                        return run_marimo(retry=False)
                    except Exception as e:
                        print(f"Failed to kill process: {e}")
            
            # If not address in use or retry failed
            print("WARNING: Manual Analysis (Marimo) will not be available.")
            log_file.close()
            return None, None
            
        print("Marimo started successfully.")
        return process, log_file

    def run_redis(retry=True):
        print(f"Starting Redis server on port {REDIS_PORT}...")
        # Use absolute path for DATA_DIR to be safe with --dir
        abs_data_dir = os.path.abspath(DATA_DIR)
        cmd = [
            "redis-server",
            "--port", str(REDIS_PORT),
            "--dir", abs_data_dir,
            "--save", "60 1", # Basic persistence to data/
            "--appendonly", "no"
        ]
        # Log to file in data/ for debugging
        log_path = os.path.join(DATA_DIR, "redis.log")
        log_file = open(log_path, "w+")
        process = subprocess.Popen(cmd, stdout=log_file, stderr=log_file)
        
        # Check if it failed immediately
        time.sleep(2)
        if process.poll() is not None:
            # It died. Check why.
            log_file.seek(0)
            output = log_file.read()
            print(f"Redis failed to start. Output:\n{output[-500:]}")
            
            if "Address already in use" in output or "address already in use" in output:
                if retry:
                    print(f"Port {REDIS_PORT} in use. Attempting to kill existing process...")
                    try:
                        subprocess.run(["fuser", "-k", f"{REDIS_PORT}/tcp"], check=False)
                        time.sleep(1) # Wait for release
                        return run_redis(retry=False)
                    except Exception as e:
                        print(f"Failed to kill process: {e}")
            
            # If not address in use or retry failed
            print("WARNING: Live Context (Redis) will not be available.")
            log_file.close()
            return None, None
            
        print("Redis started successfully.")
        return process, log_file

    redis_process, redis_log = run_redis()
    marimo_process, marimo_log = run_marimo()
    
    def cleanup(signum=None, frame=None):
        print("Stopping Marimo server...")
        if marimo_process:
            marimo_process.terminate()
            try:
                marimo_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                marimo_process.kill()
        if marimo_log:
            try:
                marimo_log.close()
            except:
                pass
        
        print("Stopping Redis server...")
        if redis_process:
            redis_process.terminate()
            try:
                redis_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                redis_process.kill()
        if redis_log:
            try:
                redis_log.close()
            except:
                pass
            
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    uvicorn.run(app, host=API_HOST, port=API_PORT)



