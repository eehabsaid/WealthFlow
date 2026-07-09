import urllib.request as _ur
import json as _json

def fetch_latest_exchange_rates(user_agent: str = "SalaryTracker/1.0") -> dict:
    url = "https://open.er-api.com/v6/latest/EGP"
    req = _ur.Request(url, headers={"User-Agent": user_agent})
    with _ur.urlopen(req, timeout=15) as resp:
        data = _json.loads(resp.read().decode())
    if data.get("result") != "success":
        raise ValueError("API returned non-success")
    return data.get("rates", {})
