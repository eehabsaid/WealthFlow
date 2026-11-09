"""Move all AI code into ai/ with gates.  Usage:
  python scripts/ai_move.py            dry-run: map + gates on a temp copy, write report
  python scripts/ai_move.py --apply    same, then perform the move if every gate is clean
  python scripts/ai_move.py --verify   after the move: rescan the real tree with AI_MOVE_MAP.json
Writes AI_MOVE_MAP.json and AI_MOVE_REPORT.txt into the repo root.
"""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ai_move_lib import astfix, imports, inventory, rewrite, scaffold  # noqa: E402

ROOT = os.path.dirname(HERE)


def map_mod(name, mmap):
    for k in sorted(mmap, key=len, reverse=True):
        if name == k or name.startswith(k + "."):
            return mmap[k] + name[len(k):]
    return name


def perform(root, fmap, mmap):
    mods = {m: r for m, r in imports._modules(root).items()}
    origins = astfix.aggregator_origins(root, mods, mmap)
    fixed = [r for r in sorted(mods.values()) if astfix.fix_file(root, r, mods, mmap, origins)]
    for old, new in sorted(fmap.items()):
        dst = os.path.join(root, new)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(os.path.join(root, old), dst)
    pats = rewrite.build_patterns(fmap, mmap)
    changed = rewrite.rewrite_tree(root, pats)
    scaffold.apply(root)
    return fixed, changed, origins


def gates(root_old, root_new, fmap, mmap, origins):
    u0, e0 = imports.analyse(root_old)
    c0 = imports.cycles(e0)
    u1, e1 = imports.analyse(root_new)
    c1 = imports.cycles(e1)
    exp_u = {(fmap.get(r, r), map_mod(b, mmap), n) for r, b, n in u0}
    new_u = sorted(x for x in u1 if x not in exp_u)
    exp_c = sorted(sorted(map_mod(m, mmap) for m in c) for c in c0)
    new_c = [c for c in c1 if c not in exp_c]
    pats = rewrite.old_ref_patterns(fmap, mmap)
    refs = rewrite.scan_old_refs(root_new, pats)
    return {"baseline_unresolved": len(u0), "new_unresolved": new_u,
            "baseline_cycles": len(c0), "new_cycles": new_c, "old_refs": refs}


# Deliberate old-path strings: this test asserts that the old modules no longer exist.
EXPECTED_OLD_REFS = {"ai/tests/test_ai_app_layout.py"}


def verify():
    """Post-move scan of the real tree: unresolved imports, cycles, old-path references, missing targets."""
    with open(os.path.join(ROOT, "AI_MOVE_MAP.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    fmap, mmap = data["files"], data["modules"]
    unresolved, edges = imports.analyse(ROOT)
    cyc = imports.cycles(edges)
    refs = rewrite.scan_old_refs(ROOT, rewrite.old_ref_patterns(fmap, mmap))
    refs = [r for r in refs if r[0] not in EXPECTED_OLD_REFS]
    missing = [n for n in sorted(fmap.values()) if not os.path.exists(os.path.join(ROOT, n))]
    left = [o for o in sorted(fmap) if os.path.exists(os.path.join(ROOT, o))]
    lines = ["", "POST-MOVE VERIFICATION (real tree)",
             f"mapped targets missing: {len(missing)}", *missing[:20],
             f"old files still present: {len(left)}", *left[:20],
             f"unresolved imports: {len(unresolved)}", *map(str, sorted(unresolved)[:40]),
             f"circular dependencies: {len(cyc)}", *map(str, cyc[:5]),
             f"remaining old-path references: {len(refs)}", *map(str, refs[:40])]
    ok = not (missing or left or unresolved or refs or len(cyc) > 1)  # 1 cycle = pre-existing baseline (provider factory)
    lines.append("RESULT: " + ("CLEAN" if ok else "NOT CLEAN"))
    with open(os.path.join(ROOT, "AI_MOVE_REPORT.txt"), "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines[:1] + [l for l in lines if l.startswith(("mapped", "old files", "unresolved", "circular", "remaining", "RESULT"))]))
    return 0 if ok else 1


def main():
    if "--verify" in sys.argv:
        return verify()
    apply_it = "--apply" in sys.argv
    fmap = inventory.build_file_map(ROOT)
    mmap = inventory.build_module_map(fmap)
    with open(os.path.join(ROOT, "AI_MOVE_MAP.json"), "w", encoding="utf-8") as fh:
        json.dump({"files": fmap, "modules": mmap}, fh, indent=1, sort_keys=True)
    tmp = tempfile.mkdtemp(prefix="ai_move_")
    work = os.path.join(tmp, "copy")
    ign = shutil.ignore_patterns("node_modules", ".git", "__pycache__", "*.sqlite3")
    shutil.copytree(ROOT, work, ignore=ign)
    fixed, changed, origins = perform(work, fmap, mmap)
    g = gates(ROOT, work, fmap, mmap, origins)
    clean = not (g["new_unresolved"] or g["new_cycles"] or g["old_refs"])
    lines = [f"files mapped: {len(fmap)}  module renames: {len(mmap)}",
             f"python files import-fixed: {len(fixed)}  text files rewritten: {len(changed)}",
             f"baseline unresolved imports: {g['baseline_unresolved']}  baseline cycles: {g['baseline_cycles']}",
             f"NEW unresolved imports: {len(g['new_unresolved'])}", *map(str, g["new_unresolved"][:60]),
             f"NEW circular dependencies: {len(g['new_cycles'])}", *map(str, g["new_cycles"][:10]),
             f"remaining old-path references: {len(g['old_refs'])}", *map(str, g["old_refs"][:80]),
             "RESULT: " + ("CLEAN" if clean else "NOT CLEAN - move refused")]
    with open(os.path.join(ROOT, "AI_MOVE_REPORT.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines[:4] + lines[-1:]))
    if apply_it and clean:
        perform(ROOT, fmap, mmap)
        print("applied")
    elif apply_it:
        print("REFUSED: see AI_MOVE_REPORT.txt")
    shutil.rmtree(tmp, ignore_errors=True)
    return 0 if clean else 1


if __name__ == "__main__":
    sys.exit(main())
