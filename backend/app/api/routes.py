import json
from fastapi import APIRouter, HTTPException, Body
from pathlib import Path
from backend.app.core.paths import PRODUCTS

router = APIRouter(prefix="/api")

def get_manifest_path(sku: str) -> Path:
    path = PRODUCTS / sku / "manifest.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Manifest not found")
    return path

@router.get("/products")
def list_products():
    """Returns a list of all processed products."""
    products = []
    if not PRODUCTS.exists():
        return products
        
    for product_dir in PRODUCTS.iterdir():
        if product_dir.is_dir():
            manifest_file = product_dir / "manifest.json"
            if manifest_file.exists():
                try:
                    with open(manifest_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        # Safely append the data inside the 'with' block
                        products.append({
                            "sku": data.get("sku", product_dir.name),
                            "title": data.get("title", "No Title"),
                            "status": data.get("status", "discovered"),
                            "garment_type": data.get("garment_type"),
                            "condition": data.get("condition"),
                        })
                except json.JSONDecodeError:
                    # Skip corrupted or empty JSON files so the dashboard still loads
                    continue
    return products

@router.get("/products/{sku}")
def get_product(sku: str):
    """Returns the full manifest data for a specific product."""
    manifest_path = get_manifest_path(sku)
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)

@router.post("/products/{sku}")
def update_product(sku: str, updated_data: dict = Body(...)):
    """Saves edited data back to the manifest.json file."""
    manifest_path = get_manifest_path(sku)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(updated_data, f, indent=4, ensure_ascii=False)
    return {"status": "success", "message": f"Successfully updated {sku}"}