from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="ListingAI Review Dashboard")

# Import routers
from backend.app.api.drafts import router as drafts_router
from backend.app.api.routes import router as products_router

# Register routers
app.include_router(products_router)
app.include_router(drafts_router)

# Debug print
print("=" * 60)
print("🚀 REGISTERED API ROUTES:")
for route in app.routes:
    if hasattr(route, "path") and hasattr(route, "methods"):
        print(f"  {list(route.methods)} {route.path}")
print("=" * 60)

# Static files
PROJECT_ROOT = Path(__file__).resolve().parents[2]
static_dir = PROJECT_ROOT / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def read_index():
    html_path = static_dir / "index.html"
    if not html_path.exists():
        return PlainTextResponse(f"404: {html_path} not found", status_code=404)
    return FileResponse(html_path)
