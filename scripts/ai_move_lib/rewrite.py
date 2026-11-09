"""Text rewrite (dotted modules, paths, template/static strings) + remaining-ref scan."""
import os
import re

from . import inventory, rules

SINGLE = {"ai_training", "doc_engine", "dev_agent", "ai_knowledge"}


def _single_res(old, new):
    o = re.escape(old)
    return [
        (re.compile(rf"(?<![\w.]){o}(?=\.\w)"), new),
        (re.compile(rf"(?<=from ){o}(?=\s+import)"), new),
        (re.compile(rf"(?<=import ){o}\b(?![\w.])"), new),
        (re.compile(rf"(?<=-m ){o}\b"), new),
        (re.compile(rf"""(?<=['"]-m['"], ['"]){o}(?=['"])"""), new),
    ]


def build_patterns(fmap, mmap):
    pats = []
    dotted = dict(mmap)
    for old, new in rules.RULES:
        if not old.endswith(".py"):
            dotted[old.replace("/", ".")] = new.replace("/", ".")
    dotted[rules.TEST_ROOT_OLD.replace("/", ".")] = rules.TEST_ROOT_GENERIC.replace("/", ".")
    multi = {k: v for k, v in dotted.items() if k not in SINGLE}
    if multi:
        keys = sorted(multi, key=len, reverse=True)
        rx = re.compile(r"(?<![\w.])(" + "|".join(map(re.escape, keys)) + r")(?![\w])")
        pats.append((rx, lambda m: multi[m.group(1)]))
    for s in SINGLE:
        if s in dotted:
            pats += _single_res(s, dotted[s])
    paths = {}
    for old, new in rules.RULES:
        paths[old] = new
    paths[rules.TEST_ROOT_OLD] = rules.TEST_ROOT_GENERIC
    for old in sorted(paths, key=len, reverse=True):
        o = re.escape(old)
        pre = r"(?:(?<![\w/\\.])|(?<=\./)|(?<=\.\\))"
        bs = o.replace("/", "[\\\\]")
        pats.append((re.compile(pre + o + "(?=/)"), paths[old]))
        dbl = o.replace("/", "[\\\\][\\\\]")  # escaped backslashes inside JSON / Python string literals
        pats.append((re.compile(pre + dbl + "(?=[\\\\][\\\\])"), paths[old].replace("/", "\\\\")))
        pats.append((re.compile(pre + bs + "(?=[\\\\])"), paths[old].replace("/", "\\")))
    for rx, rep, _ in rules.EXTRA_STRING_RULES:
        pats.append((re.compile(rx), rep))
    return pats


def rewrite_text(text, pats):
    for rx, rep in pats:
        text = rx.sub(rep if callable(rep) else (lambda m, r=rep: r), text)
    return text


GENERATED = {"AI_MOVE_MAP.json", "AI_MOVE_REPORT.txt"}


def text_files(root):
    for rel in inventory.walk(root):
        if rel in GENERATED or rel.startswith(("scripts/ai_move_lib/", "scripts/ai_move.py")):
            continue
        if os.path.splitext(rel)[1] in rules.TEXT_EXT or rel.endswith(("README", "Dockerfile")):
            yield rel


def rewrite_tree(root, pats):
    changed = []
    for rel in text_files(root):
        p = os.path.join(root, rel)
        try:
            with open(p, encoding="utf-8", newline="") as fh:
                src = fh.read()
        except UnicodeDecodeError:
            continue
        new = rewrite_text(src, pats)
        if new != src:
            with open(p, "w", encoding="utf-8", newline="") as fh:
                fh.write(new)
            changed.append(rel)
    return changed


def old_ref_patterns(fmap, mmap):
    """Patterns that must have 0 hits after the move (same shapes the rewrite targets)."""
    pats = build_patterns(fmap, mmap)
    return [rx for rx, _ in pats if rx.pattern]


def scan_old_refs(root, patterns):
    hits = []
    for rel in text_files(root):
        try:
            with open(os.path.join(root, rel), encoding="utf-8") as fh:
                src = fh.read()
        except UnicodeDecodeError:
            continue
        for i, line in enumerate(src.split("\n"), 1):
            if any(a in line for a in rules.ALLOWED_OLD_STRINGS) and not any(
                    rx.search(line.replace("core.ai.pipeline", "")) for rx in patterns):
                continue
            for rx in patterns:
                if rx.search(line.replace("core.ai.pipeline", "")):
                    hits.append((rel, i, line.strip()[:140]))
                    break
    return hits
