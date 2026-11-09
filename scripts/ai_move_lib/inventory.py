"""Walk the repo and build the old->new file map and module map."""
import os
import re

from . import rules

FINANCE_RE = re.compile(
    r"\b(Expense|Salary|Balance|Budget|FixedAsset|BankAccount|Certificate|Goal|Scenario|"
    r"Reminder|Gold|Currency|ExchangeRate|IncomeAdjustment|Company|BankCertificate)\w*"
    r"|core\.services\.(expenses|salary|balance|budget|fixed_assets|goals|scenario|"
    r"reminders|certificate|bank|gold|currency|exchange)")


def walk(root):
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in rules.SKIP_DIRS]
        for f in files:
            if f in rules.SKIP_FILES or f.endswith(".pyc"):
                continue
            yield os.path.relpath(os.path.join(base, f), root).replace(os.sep, "/")


def is_finance_test(root, rel):
    try:
        with open(os.path.join(root, rel), encoding="utf-8", errors="ignore") as fh:
            return bool(FINANCE_RE.search(fh.read()))
    except OSError:
        return False


def build_file_map(root):
    files = sorted(walk(root))
    fmap = {}
    for rel in files:
        new = None
        if rel == rules.TEST_ROOT_OLD or rel.startswith(rules.TEST_ROOT_OLD + "/"):
            tail = rel[len(rules.TEST_ROOT_OLD) + 1:] if rel != rules.TEST_ROOT_OLD else ""
            if tail.endswith("__init__.py") and "/" not in tail:
                new = f"{rules.TEST_ROOT_GENERIC}/__init__.py"
            elif rel.endswith(".py") and is_finance_test(root, rel):
                new = f"{rules.TEST_ROOT_FINANCE}/{tail}"
            else:
                new = f"{rules.TEST_ROOT_GENERIC}/{tail}"
            del keep_generic
        else:
            for old, tgt in rules.RULES:
                if rel == old or rel.startswith(old + "/"):
                    new = tgt + rel[len(old):]
                    break
        if new and new != rel:
            fmap[rel] = new
    return fmap


def to_module(path):
    if not path.endswith(".py"):
        return None
    p = path[:-3]
    if p.endswith("/__init__"):
        p = p[: -len("/__init__")]
    return p.replace("/", ".")


def build_module_map(fmap):
    out = {}
    for old, new in fmap.items():
        a, b = to_module(old), to_module(new)
        if a and b and a != b:
            out[a] = b
    return out
