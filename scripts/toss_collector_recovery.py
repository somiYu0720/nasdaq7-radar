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
    categories = watch.get("categories", {}) if "categories" in watch else json.loads(base64.b64decode(watch["content"])).get("categories", {})
    symbols = sorted(set(categories.get("nas", []) + categories.get("china", [])))
    print("Watchlist symbols:", len(symbols))
    if not symbols:
        raise ValueError("Watchlist is empty; refusing to overwrite live data")
    print("Collector running. Stop with Pydroid stop button.")
    while True:
        rows = []
        for symbol in symbols:
            try:
                quote = unwrap(api_get("/api/v1/prices", token, {"symbols": symbol}))
                bar = unwrap(api_get("/api/v1/candles", token, {"symbol": symbol, "interval": "1m", "count": 1}))
                price, volume = quote.get("lastPrice"), bar.get("volume")
                if price is None or volume is None:
                    print(symbol, "MISSING_FIELDS")
                    continue
                rows.append({"ticker": symbol,
                    "categories": [k for k in CATEGORIES if symbol in categories.get(k, [])],
                    "price": price, "minute_volume": volume,
                    "quote_time": quote.get("timestamp"), "bar_time": bar.get("timestamp"),
                    "collected_utc": now_utc()})
            except urllib.error.HTTPError as error:
                print(symbol, "HTTP", error.code)
            except Exception as error:
                print(symbol, "ERROR", type(error).__name__)
        print("Collected", len(rows), "/", len(symbols))
        if rows:
            try:
                github_put("toss_live.json", gh, {
                    "source": "toss_mobile",
                    "status": "ok" if len(rows) == len(symbols) else "partial",
                    "updated_utc": now_utc(), "rows": rows})
                print("UPLOAD_OK", now_utc())
            except urllib.error.HTTPError as error:
                print("UPLOAD_HTTP_ERROR", error.code)
            except Exception as error:
                print("UPLOAD_ERROR", type(error).__name__)
        else:
            print("NO_UPLOAD: 0 successful records")
        time.sleep(INTERVAL_SECONDS)
except KeyboardInterrupt:
    print("Stopped")
except urllib.error.HTTPError as e:
    print("HTTP_STATUS:", e.code)
    print("RESULT: REQUEST_FAILED")
except Exception as e:
    print("RESULT: TEST_FAILED", type(e).__name__, str(e)[:120])
