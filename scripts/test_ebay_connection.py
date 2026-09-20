import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.ebay.client import test_connection

def main():
    print("Testing eBay Sandbox Connection...")
    if test_connection():
        print("✅ SUCCESS: Connected to eBay Sandbox!")
    else:
        print("❌ FAILED: Check your EBAY_USER_TOKEN in .env")

if __name__ == "__main__":
    main()