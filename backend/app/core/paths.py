from pathlib import Path

# The project root is 3 directories up from this file:
# paths.py -> core -> app -> backend -> listing-ai (root)
ROOT = Path(__file__).resolve().parents[3]
BASE_DIR = ROOT  # Alias for modern naming

# Core directories
PICTURES = ROOT / "Pictures"
PROCESSED = ROOT / "Processed"

# Storage directories
PRODUCTS = ROOT / "storage" / "products"
STORAGE_PRODUCTS = PRODUCTS  # Alias

LOGS = ROOT / "logs"

# Working directories for generated listing drafts and cached vision output
DRAFTS = ROOT / "drafts"
TEMP = ROOT / "temp"

# Ensure critical directories exist
for directory in [PICTURES, PROCESSED, PRODUCTS, LOGS, DRAFTS, TEMP]:
    directory.mkdir(parents=True, exist_ok=True)
