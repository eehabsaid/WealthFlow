"""Gulf module helpers: a throwaway Member user per currency, driven through the real API.

A fresh account is required: an existing account whose data references EGP (balances, expenses...) correctly keeps its
EGP row, so only a brand-new user shows the "no EGP anywhere" behavior of a Gulf user."""

import time

_POST_JS = """async ([url, payload]) => {
    const token = (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '';
    const r = await fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': token},
                                body: JSON.stringify(payload)});
    let body = null; try { body = await r.json(); } catch (e) {}
    return {status: r.status, body};
}"""

GULF_TEST_PASSWORD = "GulfE2e-Pass-1!"


def api_json(page, url):
    return page.evaluate("async (u) => { const r = await fetch(u); return r.ok ? await r.json() : null; }", url)


def api_post(page, url, payload):
    return page.evaluate(_POST_JS, [url, payload])


def create_member_user(admin_page, code):
    """Admin creates a fresh user holding the Member role. Returns (user_id, username) or (None, reason)."""
    username = f"e2e_{code.lower()}_{str(int(time.time() * 1000))[-6:]}"
    made = api_post(admin_page, "/api/users/", {"username": username, "email": f"{username}@example.com",
                                                 "password": GULF_TEST_PASSWORD})
    if made.get("status") != 201:
        return None, f"create user failed: {made}"
    user_id = made["body"]["user"]["id"]
    roles = (api_json(admin_page, "/api/roles/") or {}).get("roles", [])
    member = next((r for r in roles if str(r.get("name", "")).lower() == "member"), None)
    if member is None:
        return user_id, "Member role not found"
    api_post(admin_page, f"/api/users/{user_id}/roles/", {"role_id": member["id"]})
    return user_id, username


def delete_user(admin_page, user_id):
    return api_post(admin_page, "/api/users/bulk/", {"action": "delete", "ids": [user_id]})
