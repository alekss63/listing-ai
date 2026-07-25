from fastapi import FastAPI

app = FastAPI(
    title="Claude eBay Listing Assistant",
    version="1.0.0"
)


@app.get("/")
def home():
    return {
        "status": "running",
        "project": "Claude eBay Listing Assistant"
    }
