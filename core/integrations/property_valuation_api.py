import json
from urllib import error, request

def fetch_property_external_valuation(url: str, timeout_seconds: float, headers: dict):
    req = request.Request(url=url, headers=headers, method="GET")
    try:
        with request.urlopen(req, timeout=timeout_seconds) as resp:
            body = resp.read()
    except (error.URLError, error.HTTPError, TimeoutError, ValueError):
        return None

    if not body:
        return None

    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, TypeError, ValueError, json.JSONDecodeError):
        try:
            return float(body)
        except (TypeError, ValueError):
            return None
