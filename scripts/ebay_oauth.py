import base64
import os
import sys
import urllib.parse
from pathlib import Path

import httpx
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

APP_ID = os.getenv("EBAY_APP_ID")
CERT_ID = os.getenv("EBAY_CERT_ID")
RUNAME = os.getenv("EBAY_RUNAME", "Alex_Miles-AlexMile-Claude-srdtrbwfd")

AUTH_ENDPOINT = "https://auth.sandbox.ebay.com/oauth2/authorize"
TOKEN_ENDPOINT = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"

SCOPES = [
    "https://api.ebay.com/oauth/api_scope",
    "https://api.ebay.com/oauth/api_scope/sell.account",
    "https://api.ebay.com/oauth/api_scope/sell.inventory",
    "https://api.ebay.com/oauth/api_scope/sell.fulfillment",
]


def main():
    if not APP_ID or not CERT_ID:
        print("❌ Add EBAY_APP_ID and EBAY_CERT_ID to .env first!")
        return

    params = {
        "client_id": APP_ID,
        "redirect_uri": RUNAME,
        "response_type": "code",
        "scope": " ".join(SCOPES),
    }
    auth_url = AUTH_ENDPOINT + "?" + urllib.parse.urlencode(params)

    print("1) Open this URL in your browser and sign in with your SELLER test user:\n")
    print(auth_url)
    print("\n2) Click 'Agree and Continue'. The browser will then show an error page.")
    print("   That's OK! Copy the value after ?code= from the address bar.\n")
    code = input("3) Paste the code (or the full URL) here and press Enter: ").strip()

    if "code=" in code:
        parsed = urllib.parse.urlparse(code)
        code = urllib.parse.parse_qs(parsed.query).get("code", [code])[0]

    credentials = base64.b64encode(f"{APP_ID}:{CERT_ID}".encode()).decode()
    response = httpx.post(
        TOKEN_ENDPOINT,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "authorization_code", "code": code, "redirect_uri": RUNAME},
        timeout=15.0,
    )
    result = response.json()

    if "access_token" in result:
        print("\n✅ SUCCESS! Your scoped User Access Token:\n")
        print(result["access_token"])
        print("\n👉 Paste this into .env as EBAY_USER_TOKEN (replace the old one).")
        if "refresh_token" in result:
            print("\nRefresh token (keep it safe, we'll use it later):")
            print(result["refresh_token"])
    else:
        print("\n❌ Token exchange failed:")
        print(result)


if __name__ == "__main__":
    main()