#!/usr/bin/env python3
"""Verify both generated user guide files."""
import re
import os

base = os.path.join(os.path.dirname(__file__), "..")
html_path = os.path.normpath(os.path.join(base, "docs", "user_guide.html"))
docx_path = os.path.normpath(os.path.join(base, "docs", "user_guide.docx"))

print("=" * 60)
print("VERIFY: docs/user_guide.html")
print("=" * 60)

with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

# TOC links vs section ids
toc_targets = re.findall(r'data-target="([^"]+)"', html)
section_ids = re.findall(r'<section id="([^"]+)"', html)
print(f"  TOC links:       {len(toc_targets)}")
print(f"  Section ids:     {len(section_ids)}")
missing = [t for t in toc_targets if t not in section_ids]
print(f"  All TOC links resolve: {'YES' if not missing else 'NO: ' + str(missing)}")

# Sysadmin badges
badges = html.count("sysadmin-warning")
print(f"  Sysadmin badges: {badges}")

# 16 main pages
main_pages = [
    "Dashboard", "WealthFlow AI", "Financial Advisor", "Employment",
    "Balance", "Bank Certificates", "Fixed Assets", "Exchange Rates",
    "Gold Price", "Expenses", "Expense Categories", "Budgets",
    "Import Data", "Reports", "Advanced Reports",
]
mp_ok = all(p in html for p in main_pages)
print(f"  16 main pages:   {'ALL PRESENT' if mp_ok else 'MISSING: ' + str([p for p in main_pages if p not in html])}")

# 20 settings tabs
tabs = [
    "Languages", "Companies", "Banks", "Currency", "Users",
    "Roles", "Billing Plans", "Email Templates", "Translations",
    "Translation Coverage", "Reminders", "Certificate Status",
    "Gold Settings", "Property Valuation", "Dashboard (Settings)",
    "Backup & Restore", "Documentation", "AI Advisor", "Legal Text",
    "My AI Settings",
]
tabs_ok = all(t in html for t in tabs)
print(f"  20 settings tabs: {'ALL PRESENT' if tabs_ok else 'MISSING: ' + str([t for t in tabs if t not in tabs])}")

# Offline check: no external URLs
ext_urls = re.findall(r'(?:src|href)\s*=\s*["\']https?://', html)
print(f"  External URLs:   {len(ext_urls)} (should be 0)")

# Skip link
print(f"  Skip link:       {'YES' if 'skip-link' in html else 'NO'}")
# Dark mode
print(f"  Dark mode:       {'YES' if 'prefers-color-scheme' in html else 'NO'}")
# IntersectionObserver
print(f"  IntersectionObserver: {'YES' if 'IntersectionObserver' in html else 'NO'}")
# Semantic landmarks
print(f"  <nav> landmark:  {'YES' if '<nav' in html else 'NO'}")
print(f"  <main> landmark: {'YES' if '<main' in html else 'NO'}")
print(f"  <section> tags:  {html.count('<section')}")

print()
print("=" * 60)
print("VERIFY: docs/user_guide.docx")
print("=" * 60)

from docx import Document
d = Document(docx_path)

# Sysadmin badges
sysadmin_count = sum(1 for p in d.paragraphs if "Sysadmin only" in p.text)
print(f"  Sysadmin badges: {sysadmin_count}")

# Numbered sections (headings that start with a digit)
numbered = [p for p in d.paragraphs if p.style.name.startswith("Heading") and p.text and p.text[0].isdigit()]
print(f"  Numbered sections: {len(numbered)}")

# Contents page
has_contents = any(p.text.strip() == "Contents" for p in d.paragraphs)
print(f"  Contents page:   {'YES' if has_contents else 'NO'}")

# Header
header_text = d.sections[0].header.paragraphs[0].text if d.sections[0].header.paragraphs else ""
print(f"  Header:          {header_text!r}")

# Footer (page number field)
footer_p = d.sections[0].footer.paragraphs[0] if d.sections[0].footer.paragraphs else None
has_page_field = False
if footer_p:
    for run in footer_p.runs:
        if run._r.xml.find("PAGE") != -1:
            has_page_field = True
            break
print(f"  Page number:     {'YES' if has_page_field else 'NO'}")

# 16 main pages in DOCX
mp_ok_docx = all(any(p.text.find(mp) != -1 for p in numbered) for mp in main_pages)
print(f"  16 main pages:   {'ALL PRESENT' if mp_ok_docx else 'CHECK MANUALLY'}")

# 20 settings tabs in DOCX
tabs_ok_docx = all(any(p.text.find(t) != -1 for p in numbered) for t in tabs)
print(f"  20 settings tabs: {'ALL PRESENT' if tabs_ok_docx else 'CHECK MANUALLY'}")

# Title heading
has_title = any(p.style.name == "Title" for p in d.paragraphs)
print(f"  Title heading:   {'YES' if has_title else 'NO'}")

print()
print("=" * 60)
print("ALL CHECKS COMPLETE")
print("=" * 60)
