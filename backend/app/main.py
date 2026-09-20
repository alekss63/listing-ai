from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.routes import router

app = FastAPI(title="ListingAI Review Dashboard")

# Include API routes
app.include_router(router)

# Calculate paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
static_dir = PROJECT_ROOT / "static"
static_dir.mkdir(exist_ok=True)

# DEBUG PRINTS: Look at your terminal when you start the server!
print("=" * 50)
print(f"PROJECT ROOT DETECTED AS: {PROJECT_ROOT}")
print(f"LOOKING FOR HTML AT: {static_dir / 'index.html'}")
print(f"FILE EXISTS? {(static_dir / 'index.html').exists()}")
print("=" * 50)

app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def read_index():
    html_path = static_dir / "index.html"

    # If the file is missing, tell us exactly where it was looking
    if not html_path.exists():
        return PlainTextResponse(
            f"404 Not Found\n\nI am looking for index.html here:\n{html_path}\n\nBut it does not exist!\nPlease make sure the 'static' folder is at the root of your project.",
            status_code=404,
        )

    return FileResponse(html_path)
