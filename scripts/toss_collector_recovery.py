"""NASDAQ 7.0 mobile collector (Pydroid 3).
No trading. Runs only while this script is running.
API response schemas are not yet verified; first run is diagnostic-only.
Credentials are never saved to files or printed.
"""
import base64
import datetime as dt
import json
import time
import urllib.error
import urllib.parse
import urllib.request

REPO = "somiYu0720/nasdaq7-radar"
BASE = "https://openapi.tossinvest.com"
GITHUB_API = "https://api.github.com/repos/" + REPO + "/contents/"
CATEGORIES = ("nas", "china")
INTERVAL_SECONDS = 60

def call(url, method="GET", headers=None, data=None):
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)

def now_utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def api_get(path, token, params):
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    return call(url, headers={"Authorization": "Bearer " + token})

def github_get(path, gh):
    return call(GITHUB_API + path, headers={
        "Authorization": "Bearer " + gh,
        "Accept": "application/vnd.github+json",
        "User-Agent": "nasdaq7-mobile-collector",
    })

def github_put(path, gh, document):
    old = github_get(path, gh)
    body = {
        "message": "Update Toss mobile market snapshot",
        "content": base64.b64encode(json.dumps(document, ensure_ascii=False).encode()).decode(),
        "sha": old["sha"],
    }
    return call(GITHUB_API + path, "PUT", {
        "Authorization": "Bearer " + gh,
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "nasdaq7-mobile-collector",
    }, json.dumps(body).encode())

def unwrap(data):
    if isinstance(data, list):
        return data[0] if data else {}
    if not isinstance(data, dict):
        return {}
    for key in ("data", "result", "quote", "price", "items", "prices", "candles", "bars"):
        child = data.get(key)
        if isinstance(child, dict):
            return unwrap(child)
        if isinstance(child, list) and child:
            return unwrap(child)
    return data

def get_field(d, keys):
    for k in keys:
        if d.get(k) is not None:
            return d[k]
    return None

def token_for(cid, secret):
    payload = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": cid,
        "client_secret": secret,
    }).encode()
    data = call(BASE + "/oauth2/token", "POST",
                {"Content-Type": "application/x-www-form-urlencoded"}, payload)
    return data["access_token"]

print("NASDAQ 7.0 | Toss mobile collector")
print("Do not share screenshots containing entered credentials.")
cid = input("TOSS_CLIENT_ID: ").strip()
secret = input("TOSS_CLIENT_SECRET: ").strip()
gh = input("GitHub token (repo write access): ").strip()
if not cid or not secret or not gh:
    raise SystemExit("Missing credential. Nothing uploaded.")
try:
    token = token_for(cid, secret)
    print("AUTH_OK")
    watch = github_get("watchlist.json", gh)
    categories = watch.get("categories", {})
    symbols = sorted(set(categories.get("nas", []) + categories.get("china", [])))
    print("Watchlist symbols:", len(symbols))
    # First inspect one real response before assuming quote/bar field names.
    sample = symbols[0] if symbols else "LUCD"
    q = api_get("/api/v1/prices", token, {"symbols": sample})
    b = api_get("/api/v1/candles", token, {
        "symbol": sample, "interval": "1m", "count": 1
    })
    quote_obj, bar_obj = unwrap(q), unwrap(b)
    print("QUOTE_FIELDS:", sorted(quote_obj.keys()))
    print("BAR_FIELDS:", sorted(bar_obj.keys()))
    print("TEST_SYMBOL:", sample)
    print("No upload yet: response field mapping must be checked first.")
    print("RESULT: DIAGNOSTIC_COMPLETE")
except urllib.error.HTTPError as e:
    print("HTTP_STATUS:", e.code)
    print("RESULT: REQUEST_FAILED (no upload)")
except Exception as e:
    print("RESULT: TEST_FAILED", type(e).__name__, "(no upload)")
