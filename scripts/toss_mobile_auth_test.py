"""Pydroid 3: Toss API authentication diagnostic. No orders, no uploads.
Run locally. Never send credentials or tokens in screenshots.
"""
import json
import urllib.parse
import urllib.request
import urllib.error

print("Toss API mobile connection test")
print("Credentials are used only in this process and not saved.")
client_id = input("TOSS_CLIENT_ID: ").strip()
client_secret = input("TOSS_CLIENT_SECRET: ").strip()
if not client_id or not client_secret:
    print("RESULT: MISSING_CREDENTIALS")
    raise SystemExit(1)

payload = urllib.parse.urlencode({
    "grant_type": "client_credentials",
    "client_id": client_id,
    "client_secret": client_secret,
}).encode("utf-8")
request = urllib.request.Request(
    "https://openapi.tossinvest.com/oauth2/token",
    data=payload,
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    method="POST",
)
try:
    with urllib.request.urlopen(request, timeout=20) as response:
        obj = json.load(response)
    token = obj.get("access_token")
    if not token:
        print("RESULT: TOKEN_NOT_RETURNED")
        raise SystemExit(1)
    print("RESULT: AUTH_OK")
except urllib.error.HTTPError as error:
    print("AUTH_HTTP_STATUS:", error.code)
    print("RESULT:", "IP_NOT_ALLOWED_OR_FORBIDDEN" if error.code == 403 else "AUTH_FAILED")
    raise SystemExit(1)
except Exception as error:
    print("RESULT: AUTH_NETWORK_ERROR", type(error).__name__)
    raise SystemExit(1)
finally:
    client_secret = ""
    client_id = ""

quote_url = "https://openapi.tossinvest.com/api/v1/prices?" + urllib.parse.urlencode({"symbols": "LUCD"})
quote_req = urllib.request.Request(quote_url, headers={"Authorization": "Bearer " + token})
try:
    with urllib.request.urlopen(quote_req, timeout=20) as response:
        data = json.load(response)
    print("QUOTE_HTTP_STATUS: 200")
    print("QUOTE_RESPONSE_TYPE:", type(data).__name__)
    print("QUOTE_KEYS:", list(data.keys()) if isinstance(data, dict) else "list")
    print("RESULT: QUOTE_REQUEST_OK")
except urllib.error.HTTPError as error:
    print("QUOTE_HTTP_STATUS:", error.code)
    print("RESULT: QUOTE_FAILED")
except Exception as error:
    print("RESULT: QUOTE_NETWORK_ERROR", type(error).__name__)
