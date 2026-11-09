"""One-off: move AI routes out of core/urls/* into ai/urls_*.py with explicit imports."""
import ast
import os
import re

HEADER = '"""%s"""\n\nfrom django.urls import path\n\nfrom core.services.billing import feature_required\n'


def view_index(root):
    idx = {}
    for base, _d, files in os.walk(os.path.join(root, "ai/views")):
        for f in files:
            if f.endswith(".py"):
                p = os.path.join(base, f)
                mod = os.path.relpath(p, root)[:-3].replace(os.sep, ".")
                for n in ast.parse(open(p, encoding="utf-8").read()).body:
                    if isinstance(n, (ast.ClassDef, ast.FunctionDef)):
                        idx.setdefault(n.name, mod[:-9] if mod.endswith(".__init__") else mod)
    return idx


def split(root, rel, idx, keep_in_place):
    path = os.path.join(root, rel)
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    ai_imports = {}
    for n in tree.body:
        if isinstance(n, ast.ImportFrom) and n.module and n.module.startswith("ai."):
            for a in n.names:
                ai_imports[a.asname or a.name] = n.module
    lst = next(n for n in tree.body if isinstance(n, ast.Assign)
               and getattr(n.targets[0], "id", "") == "urlpatterns")
    ai_segs, core_segs, needed = [], [], {}
    for el in lst.value.elts:
        seg = ast.get_source_segment(src, el)
        names = {m.group(1) for m in re.finditer(r"\bviews\.(\w+)", seg)}
        free = {n.id for n in ast.walk(el) if isinstance(n, ast.Name)}
        is_ai = any(n in idx for n in names) or any(n in ai_imports for n in free)
        if is_ai:
            seg = re.sub(r"\bviews\.(\w+)", r"\1", seg)
            for n in names:
                needed[n] = idx[n]
            for n in free & set(ai_imports):
                needed[n] = ai_imports[n]
            ai_segs.append(seg)
        else:
            core_segs.append(seg)
    return src, tree, lst, ai_segs, core_segs, needed


def render(doc, segs, needed, extra=""):
    by = {}
    for n, m in needed.items():
        by.setdefault(m, []).append(n)
    imp = "".join(f"from {m} import {', '.join(sorted(v))}\n" for m, v in sorted(by.items()))
    body = ",\n".join("    " + s.replace("\n", "\n    ") for s in segs)
    return HEADER % doc + imp + extra + "\nurlpatterns = [\n" + body + ",\n]\n"


def rewrite_core(root, rel, src, tree, lst, core_segs):
    lines = src.split("\n")
    body = ",\n".join("    " + s.replace("\n", "\n    ") for s in core_segs) + ","
    lines[lst.value.lineno - 1:lst.value.end_lineno] = ["urlpatterns = [", body, "]"]
    text = "\n".join(lines)
    text = re.sub(r"^from ai\.[^\n]*\n", "", text, flags=re.M)
    open(os.path.join(root, rel), "w", encoding="utf-8", newline="").write(text)
