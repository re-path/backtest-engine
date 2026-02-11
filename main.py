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
    uvicorn.run(app, host="0.0.0.0", port=1218)
