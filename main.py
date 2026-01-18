import uvicorn
from core.api import *
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

app.mount("/ui", StaticFiles(directory="ui"), name="ui")

@app.get("/")
async def root():
    return RedirectResponse(url="/ui/zindex.html")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
