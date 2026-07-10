import os
import re
from pathlib import Path

BASE = Path("static")

JS_DIR = BASE / "js"
CSS_DIR = BASE / "css"

print("=" * 70)
print("FRONTEND STRUCTURE")
print("=" * 70)
print()

# ----------------------------------------------------------
# Directory Structure
# ----------------------------------------------------------

print("static/js/")
for root, dirs, files in os.walk(JS_DIR):
    level = root.replace(str(JS_DIR), "").count(os.sep)
    indent = "    " * level
    print(f"{indent}{os.path.basename(root)}/")
    subindent = "    " * (level + 1)
    for f in sorted(files):
        if f.endswith(".js"):
            fp = Path(root) / f
            try:
                lines = sum(1 for _ in open(fp, encoding="utf-8"))
                size = fp.stat().st_size
                print(f"{subindent}{f:<35} ({lines:5} lines, {size:8} bytes)")
            except:
                pass

print()

print("=" * 70)
print("JAVASCRIPT ANALYSIS")
print("=" * 70)
print()

# ----------------------------------------------------------
# JS Analysis
# ----------------------------------------------------------

func_pattern = re.compile(r'function\s+([A-Za-z0-9_]+)\s*\(')
async_pattern = re.compile(r'async\s+function\s+([A-Za-z0-9_]+)\s*\(')
const_pattern = re.compile(r'const\s+([A-Za-z0-9_]+)\s*=\s*(?:async\s*)?\(')
arrow_pattern = re.compile(r'([A-Za-z0-9_]+)\s*=\s*(?:async\s*)?\(.*?\)\s*=>')

for file in sorted(JS_DIR.rglob("*.js")):

    text = file.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()

    print("-" * 70)
    print(file.relative_to(BASE))
    print("-" * 70)

    print(f"Lines : {len(lines)}")

    functions = []

    functions += func_pattern.findall(text)
    functions += async_pattern.findall(text)
    functions += const_pattern.findall(text)
    functions += arrow_pattern.findall(text)

    functions = sorted(set(functions))

    print(f"Functions : {len(functions)}")

    if functions:
        print()

        for i, f in enumerate(functions, 1):
            print(f"{i:3}. {f}")

    print()

# ----------------------------------------------------------
# CSS
# ----------------------------------------------------------

print("=" * 70)
print("CSS ANALYSIS")
print("=" * 70)
print()

selector_pattern = re.compile(r'^([^{]+)\{', re.MULTILINE)

for file in sorted(CSS_DIR.rglob("*.css")):

    text = file.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()

    selectors = selector_pattern.findall(text)

    print("-" * 70)
    print(file.relative_to(BASE))
    print("-" * 70)

    print(f"Lines      : {len(lines)}")
    print(f"Selectors  : {len(selectors)}")
    print()

print("=" * 70)
print("DONE")
print("=" * 70)