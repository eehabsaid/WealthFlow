"""The shared redactor: secrets, emails, phone-shaped numbers and currency amounts are masked; plain numbers, dates, ids, versions and file hashes are not."""

import pytest

from ai.dev_agent.core import redact
from ai.dev_agent.core.redact import MASK

SHA256 = "a3f5" * 16
SHA1 = "9b2d" * 10

PLAIN = [
    "total = 1250.50", "balance is 1000000", "id 1234567890", "order 20261113123045", "2026-11-13", "2026-11-13T10:20:30", "100 200 300 400",
    "version 3.12.4", "line 1234: x", "pi = 3.14159265358979", "port 8080", "0x7fffffff", "1,234,567 rows", "range(1000, 2000)", "x = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]",
    "a 192.168.100.200 b", "price in EGP", "sha " + SHA256, "git " + SHA1, "$1", "$12", "cost $x", "wait 30 s", "1.2.3.4",
]


@pytest.mark.parametrize("text", PLAIN)
def test_plain_numbers_dates_ids_and_hashes_are_never_masked(text):
    assert redact.redact(text) == (text, 0)


MASKED = [
    ("mail ehab@example.com now", "mail ***REDACTED*** now"),
    ("call +20 100 123 4567 today", "call ***REDACTED*** today"),
    ("call +1-555-123-4567 today", "call ***REDACTED*** today"),
    ("call (02) 3456 7890 today", "call ***REDACTED*** today"),
    ("call 555-123-4567 today", "call ***REDACTED*** today"),
    ("call 01012345678 today", "call ***REDACTED*** today"),
    ("pay $1,200.00 now", "pay ***REDACTED*** now"),
    ("pay $42.50 now", "pay ***REDACTED*** now"),
    ("pay $100 now", "pay ***REDACTED*** now"),
    ("pay 5,000 EGP now", "pay ***REDACTED*** now"),
    ("pay EGP 5,000 now", "pay ***REDACTED*** now"),
    ("pay 75.5 USD now", "pay ***REDACTED*** now"),
    ("pay €99.99 now", "pay ***REDACTED*** now"),
    ('API_KEY = "abcd1234efgh"', f'API_KEY = "{MASK}"'),
    ("password: 'hunter2'", f"password: '{MASK}'"),
    ("key sk-abcdefghijklmnop1234 end", f"key {MASK} end"),
    ("t " + "Ab1" * 20 + " end", f"t {MASK} end"),
]


@pytest.mark.parametrize("text,expected", MASKED)
def test_secrets_emails_phones_and_amounts_with_a_currency_are_masked(text, expected):
    out, hits = redact.redact(text)
    assert out == expected and hits >= 1


@pytest.mark.parametrize("text", [
    "coding_agent/tasks/20261114-210732-how-do-x-add-work/events.jsonl:6: {}",
    "core/services/financial_advisor/cash_flow_forecast_service/forecast_v2_calc.py",
    "def test_the_repo_check_can_be_switched_off_and_reports_2_changes(self):",
    "20261114-210732-how-does-the-total-function-add-numbers",
])
def test_long_paths_slugs_and_names_are_not_tokens(text):
    assert redact.redact(text) == (text, 0)


@pytest.mark.parametrize("secret", ["aB3dE5fG7hJ9kL1mN3pQ5rS7tU9vW1xY3zA5bC7dE9fG", "q8w7e6r5t4y3u2i1o0p9a8s7d6f5g4h3j2k1l0z9x8c7v6b5"])
def test_a_stand_alone_random_token_is_still_masked(secret):
    assert redact.redact(f"token {secret} end") == (f"token {MASK} end", 1)


def test_the_old_bug_is_gone_plain_long_numbers_survive_next_to_real_pii():
    text = "id 123456789012, ts 20261113123045, mail a@b.co, 1250.50, phone +20 100 123 4567, 2026-11-13"
    out, hits = redact.redact(text)
    assert out == f"id 123456789012, ts 20261113123045, mail {MASK}, 1250.50, phone {MASK}, 2026-11-13" and hits == 2


def test_pii_can_be_switched_off_but_secrets_are_always_masked():
    text = 'a@b.co $1,200.00 +20 100 123 4567 token = "abcd1234efgh"'
    assert redact.redact(text, pii=False)[0] == f'a@b.co $1,200.00 +20 100 123 4567 token = "{MASK}"'
    assert redact.mask_pii("$1,200.00 and 5 EGP", money=False) == ("$1,200.00 and 5 EGP", 0)


def test_values_are_redacted_recursively_and_keys_are_kept():
    value = {"path": "a.py", "text": "mail a@b.co", "rows": [{"n": 5, "note": "pay $1,200.00"}, "plain 1250.50", None, True], "nested": {"deep": ["x@y.zz"]}}
    out, hits = redact.redact_value(value)
    assert out == {"path": "a.py", "text": f"mail {MASK}", "rows": [{"n": 5, "note": f"pay {MASK}"}, "plain 1250.50", None, True], "nested": {"deep": [MASK]}} and hits == 3
    assert value["text"] == "mail a@b.co", "the input is never changed"


def test_secrets_inside_json_text_are_masked_too():
    """Tool results reach the model (and the training log) as JSON text, where every quote is escaped."""
    import json
    cases = [json.dumps({"text": '3\tTOKEN = "abcd1234efgh5678"'}), json.dumps({"api_key": "abcd1234efgh"}), '{"api_key": "abcd1234efgh"}',
             json.dumps({"t": 'x "password": "hunter2hunter2" y'})]
    for text in cases:
        out, hits = redact.redact(text)
        assert hits == 1 and MASK in out and "abcd1234efgh" not in out and "hunter2" not in out, text
        json.loads(out)   # still valid JSON after masking
    assert redact.redact('{"max_tokens": 4096, "api_key": ""}') == ('{"max_tokens": 4096, "api_key": ""}', 0)


def test_masking_is_idempotent():
    once, _ = redact.redact('mail a@b.co pay $1,200.00 key = "abcd1234efgh"')
    assert redact.redact(once) == (once, 0)
