import os

import httpx
from dotenv import load_dotenv

# Force load from the exact .env file in your project root
env_path = os.path.join(os.getcwd(), ".env")
load_dotenv(dotenv_path=env_path)

domain = os.getenv("EBAY_DOMAIN", "NOT_SET")
token = os.getenv("EBAY_USER_TOKEN", "NOT_SET")

print("=" * 60)
print("🔍 EBAY API DIRECT TRUTH TEST")
print("=" * 60)
print(f"1. Domain:  {domain}")
print(f"2. Length:  {len(token)} characters")
print(f"3. Prefix:  {token[:15]}...")
print("=" * 60)

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json",
    "Content-Language": "en-US",
}

print("\n1. Testing Account Privilege (Requires 'sell.account' scope)...")
resp1 = httpx.get(f"{domain}/sell/account/v1/privilege", headers=headers, timeout=10.0)
print(f"   Status Code: {resp1.status_code}")
if resp1.status_code == 200:
    print("   ✅ SUCCESS: Token has sell.account privileges!")
else:
    print(f"   ❌ FAILED: {resp1.text[:150]}")

print("\n2. Testing Inventory API (Requires 'sell.inventory' scope)...")
resp2 = httpx.get(
    f"{domain}/sell/inventory/v1/inventory_item?limit=1", headers=headers, timeout=10.0
)
print(f"   Status Code: {resp2.status_code}")
if resp2.status_code in [
    200,
    404,
]:  # 404 is OK! It just means you have 0 items, but auth worked.
    print("   ✅ SUCCESS: Token has sell.inventory privileges!")
else:
    print(f"   ❌ FAILED: {resp2.text[:150]}")

print("=" * 60)
