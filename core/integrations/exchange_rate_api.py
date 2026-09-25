import urllib.request as _ur
import json as _json

def fetch_latest_exchange_rates(base_code: str = "EGP", user_agent: str = "SalaryTracker/1.0") -> dict:
    """Fetch latest rates quoted against `base_code` (any currency the API
    supports, e.g. the caller's own default currency) — no fixed pivot."""
    code = str(base_code or "EGP").strip().upper()
    url = f"https://open.er-api.com/v6/latest/{code}"
    req = _ur.Request(url, headers={"User-Agent": user_agent})
    with _ur.urlopen(req, timeout=15) as resp:
        data = _json.loads(resp.read().decode())
    if data.get("result") != "success":
        raise ValueError("API returned non-success")
    return data.get("rates", {})
