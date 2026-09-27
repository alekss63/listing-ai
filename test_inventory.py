import os

import httpx
from dotenv import load_dotenv

# Load .env
load_dotenv()

token = os.getenv("EBAY_USER_TOKEN")
domain = os.getenv("EBAY_DOMAIN", "https://api.ebay.com")

print(f"🔍 Testing token against: {domain}/sell/inventory/v1/inventory_item")
print(f"Token length: {len(token)}")

headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

# Try to list inventory items (requires sell.inventory scope)
response = httpx.get(
    f"{domain}/sell/inventory/v1/inventory_item?limit=1", headers=headers
)

print(f"\n📡 Status Code: {response.status_code}")
print(f"📦 Response:\n{response.text}")
