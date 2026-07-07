import os
import re
import json

FILES_TO_SCAN = []
for root, dirs, files in os.walk('static/js'):
    for file in files:
        if file.endswith('.js'):
            FILES_TO_SCAN.append(os.path.join(root, file))

for root, dirs, files in os.walk('templates'):
    for file in files:
        if file.endswith('.html'):
            FILES_TO_SCAN.append(os.path.join(root, file))

def clean_extracted_key(raw_match):
    """
    Surgically extracts the pristine key, dropping code formulas, fallback values, 
    and punctuation debris completely.
    """
    # 1. If it's a multi-argument call like t('key', 'fallback'), split cleanly by quote boundaries
    if ',' in raw_match:
        parts = re.split(r"['\"`],\s*['\"`]", raw_match)
        raw_match = parts[0]
        
    # 2. Strip quotes, escaped quotes, backticks, and structural symbols
    cleaned = raw_match.strip("'\"`\\ ")
    cleaned = re.sub(r'^\\+["\']|\\+["\']$', '', cleaned).strip("'\"` ")

    # 3. ABSOLUTE FILTER MATRIX: Reject code, math formulas, and logic elements
    if not cleaned or len(cleaned) <= 1:
        return None
    
    # Drop CSS selectors and row helper hooks
    if cleaned.startswith('.') or cleaned.startswith('#') or cleaned.endswith('-row'):
        return None
        
    # Drop Javascript expressions, variable configurations, and conditions
    bad_tokens = ['${', '?', ':', '||', '&&', '=', ';', '+', '/', '--accent', '(', ')', ',']
    if any(token in cleaned for token in bad_tokens):
        return None
        
    # Drop loop references or structural objects
    if cleaned.startswith('u.') or cleaned.startswith('item.') or cleaned.startswith('r.'):
        return None
        
    return cleaned

def scan():
    found_keys = set()
    
    # Targeted regex matchers
    js_pattern = re.compile(r"t\((.+?)\)")
    html_pattern = re.compile(r'data-i18n=["\'](.+?)["\']')
    django_pattern = re.compile(r'\{%\s*translate\s+["\'](.+?)["\']\s*%\}|\{%\s*trans\s+["\'](.+?)["\']\s*%\}')

    for file_path in FILES_TO_SCAN:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # JavaScript extraction
                for match in js_pattern.findall(content):
                    cleaned = clean_extracted_key(match)
                    if cleaned:
                        found_keys.add(cleaned)
                        
                # HTML template attribute extraction
                for match in html_pattern.findall(content):
                    cleaned = clean_extracted_key(match)
                    if cleaned:
                        found_keys.add(cleaned)
                        
                # Django backend extraction
                for match in django_pattern.findall(content):
                    for group in match:
                        if group:
                            cleaned = clean_extracted_key(group)
                            if cleaned:
                                found_keys.add(cleaned)
        except Exception as e:
            print(f"[!] Error scanning {file_path}: {e}")

    print(f"[*] Found {len(found_keys)} clean unique translation keys from code analysis.")

    # Ground Truth Reference Synced to output file
    master_path = os.path.join('static/i18n', 'en.json')
    output_path = os.path.join('static/i18n', 'en1.json')
    
    master_data = {}
    if os.path.exists(master_path):
        with open(master_path, 'r', encoding='utf-8') as f:
            master_data = json.load(f)
    else:
        print(f"[!] Warning: Master file 'en.json' not found at {master_path}. Using self-mapping values.")

    # Build fresh structured output dictionary
    synchronized_data = {}
    for key in sorted(found_keys):
        # Always retain the exact perfect value from your ground-truth en.json reference file
        synchronized_data[key] = master_data.get(key, key)
            
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(synchronized_data, f, indent=4, ensure_ascii=False)
    print(f"[+] Clean synchronization finished perfectly. File saved to: {output_path}")

if __name__ == "__main__":
    scan()