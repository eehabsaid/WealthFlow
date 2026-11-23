"""Build docs/product_docs/content.js from the per-domain JSON content files.

Usage: python scripts/build_product_docs.py [--check]
  --check : only validate that every content file is valid JSON matching the schema shape.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIR = os.path.join(ROOT, "docs", "product_docs", "content")
OUT = os.path.join(ROOT, "docs", "product_docs", "content.js")

FILES = [
    "auth_users.json",
    "dashboard_goals.json",
    "expenses_budgets.json",
    "balance_bank.json",
    "employment_salary.json",
    "fixed_assets.json",
    "advisor_ai.json",
    "settings_billing.json",
]

REQUIRED_STORY_KEYS = ["id", "title", "roles", "description", "acceptance_criteria"]
DESC_KEYS = ["as_a", "i_want", "so_that"]


def validate(doc, fname):
    errors = []
    if not isinstance(doc, dict):
        return [f"{fname}: top level must be an object"]
    if "domain" not in doc:
        errors.append(f"{fname}: missing 'domain'")
    themes = doc.get("themes") or []
    if not themes:
        errors.append(f"{fname}: no themes")
    story_count = 0
    ids = []
    for t in themes:
        for e in t.get("epics") or []:
            for f in e.get("features") or []:
                for s in f.get("stories") or []:
                    story_count += 1
                    ids.append(s.get("id"))
                    for k in REQUIRED_STORY_KEYS:
                        if k not in s:
                            errors.append(f"{fname}: story {s.get('id')!r} missing key {k}")
                    d = s.get("description") or {}
                    for k in DESC_KEYS:
                        if k not in d:
                            errors.append(f"{fname}: story {s.get('id')!r} description missing {k}")
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        errors.append(f"{fname}: duplicate story ids: {sorted(dupes)}")
    return errors, story_count


def main():
    check_only = "--check" in sys.argv
    domains = []
    all_errors = []
    total = 0
    for fname in FILES:
        path = os.path.join(CONTENT_DIR, fname)
        if not os.path.exists(path):
            all_errors.append(f"MISSING FILE: {fname}")
            continue
        with open(path, encoding="utf-8") as fh:
            try:
                doc = json.load(fh)
            except json.JSONDecodeError as e:
                all_errors.append(f"{fname}: invalid JSON: {e}")
                continue
        res = validate(doc, fname)
        if isinstance(res, tuple):
            errs, n = res
        else:
            errs, n = res, 0
        all_errors.extend(errs)
        domains.append(doc)
        total += n
        print(f"{fname}: {n} stories")
    if all_errors:
        print("\nERRORS:")
        for e in all_errors:
            print(" -", e)
        sys.exit(1)
    if check_only:
        print(f"OK — {len(domains)} domains, {total} stories, no schema errors.")
        return
    payload = {"domains": domains}
    js = "window.__DOCS__ = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n"
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(js)
    print(f"Wrote {os.path.relpath(OUT, ROOT)} ({len(js)//1024} KB) — {len(domains)} domains, {total} stories.")


if __name__ == "__main__":
    main()
