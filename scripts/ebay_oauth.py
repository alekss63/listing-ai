import base64
import os
import sys
import urllib.parse
from pathlib import Path

import httpx
from dotenv import load_dotenv
from ebay_refresh_token import update_env

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

APP_ID = os.getenv("EBAY_APP_ID")
CERT_ID = os.getenv("EBAY_CERT_ID")
RUNAME = os.getenv("EBAY_RUNAME", "Alex_Miles-AlexMile-Claude-srdtrbwfd")

EBAY_DOMAIN = os.getenv("EBAY_DOMAIN", "https://api.sandbox.ebay.com")
IS_SANDBOX = "sandbox" in EBAY_DOMAIN

AUTH_ENDPOINT = (
    "https://auth.sandbox.ebay.com/oauth2/authorize"
    if IS_SANDBOX
    else "https://auth.ebay.com/oauth2/authorize"
)
TOKEN_ENDPOINT = f"{EBAY_DOMAIN}/identity/v1/oauth2/token"

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

    account = "SELLER test user" if IS_SANDBOX else "real eBay seller account"
    print(f"Environment: {'SANDBOX' if IS_SANDBOX else 'PRODUCTION'} ({EBAY_DOMAIN})\n")
    print(f"1) Open this URL in your browser and sign in with your {account}:\n")
    print(auth_url)
    print("\n2) Click 'Agree and Continue'. The browser will then show an error page.")
    print("   That's OK! Copy the value after ?code= from the address bar.\n")
    code = input("3) Paste the code (or the full URL) here and press Enter: ").strip()

    if "code=" in code:
        parsed = urllib.parse.urlparse(code)
        code = urllib.parse.parse_qs(parsed.query).get("code", [code])[0]
    else:
        # A code copied from the address bar is still URL-encoded (%23, %5E...);
        # sending it as-is double-encodes it and eBay rejects it as invalid_grant
        code = urllib.parse.unquote(code)

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
        update_env("EBAY_USER_TOKEN", result["access_token"])
        if "refresh_token" in result:
            update_env("EBAY_REFRESH_TOKEN", result["refresh_token"])
        print("\n✅ SUCCESS! Access token and refresh token saved to .env.")
        print("   The backend now renews access tokens automatically (~18 months).")
    else:
        print("\n❌ Token exchange failed:")
        print(result)
        error = result.get("error", "")
        description = result.get("error_description", "")
        if error == "invalid_grant":
            print(
                "\n👉 The code was rejected. Codes expire ~5 minutes after you "
                "click Agree and work only once,\n   so run the script again and "
                "paste the FULL address-bar URL straight away."
            )
        elif error == "invalid_client":
            print(
                "\n👉 eBay doesn't recognise EBAY_APP_ID / EBAY_CERT_ID. Both must "
                "come from the same keyset\n   as EBAY_DOMAIN (Production keys "
                "for api.ebay.com)."
            )
        elif "redirect" in description.lower():
            print(
                "\n👉 EBAY_RUNAME doesn't match this app. Copy the RuName from "
                "the Production keyset's\n   User Tokens page (not the sandbox one)."
            )


if __name__ == "__main__":
    main()
