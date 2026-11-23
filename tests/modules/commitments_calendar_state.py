"""Commitments Calendar E2E: capture the user's ORIGINAL calendar settings and restore exactly that state.

A key with no stored value is restored by deleting it (DELETE /api/settings/?key=), never by writing a default.
"""

WINDOW_KEY = "commitments_concentration_window_days"
WEEK_KEY = "commitments_week_start_day"
KEYS = (WINDOW_KEY, WEEK_KEY)

_RESTORE = """async ([original, keys]) => {
  const csrf = (window.wfGetCsrfToken && window.wfGetCsrfToken()) || '';
  const out = {};
  for (const k of keys) {
    const v = original[k];
    const r = v === null
      ? await fetch('/api/settings/?key=' + k, {method: 'DELETE', headers: {'X-CSRFToken': csrf}})
      : await fetch('/api/settings/', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf},
                                        body: JSON.stringify({key: k, value: v})});
    out[k] = r.status;
  }
  return out;
}"""


def read_settings(context):
    """{key: stored value as string, or None when the user has no stored value}."""
    stored = context.page.evaluate("fetch('/api/settings/').then(r => r.json()).then(d => d.settings || d)")
    return {k: (str(stored[k]) if k in stored else None) for k in KEYS}


def restore_settings(context, original, keys=KEYS):
    return context.page.evaluate(_RESTORE, [original, list(keys)])
