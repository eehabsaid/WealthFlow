import os
import re
import json

# Setup
FILES_TO_SCAN = []
# Collect all JS files
for root, dirs, files in os.walk('static/js'):
    for file in files:
        if file.endswith('.js'):
            FILES_TO_SCAN.append(os.path.join(root, file))
# Add HTML templates
for root, dirs, files in os.walk('templates'):
    for file in files:
        if file.endswith('.html'):
            FILES_TO_SCAN.append(os.path.join(root, file))

def scan():
    found_keys = set()
    
    # Regex for t('key', ...)
    js_pattern = re.compile(r"t\(['\"](.+?)['\"]")
    # Regex for data-i18n="key"
    html_pattern = re.compile(r'data-i18n=["\'](.+?)["\']')

    for file_path in FILES_TO_SCAN:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            found_keys.update(js_pattern.findall(content))
            found_keys.update(html_pattern.findall(content))

    print(f"[*] Found {len(found_keys)} unique translation keys.")

    # Update JSON files
    for lang in ['en.json', 'ar.json']:
        file_path = os.path.join('static/i18n', lang)
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        added = 0
        for key in found_keys:
            if key not in data:
                data[key] = key  # Default to the key itself
                added += 1
        
        if added > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            print(f"[+] Added {added} keys to {lang}")

if __name__ == "__main__":
    scan()