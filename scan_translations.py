import os
import json

# Setup files
FILES_TO_SCAN = []
for root, _, files in os.walk('static/js'):
    for file in files:
        if file.endswith('.js'):
            FILES_TO_SCAN.append(os.path.join(root, file))

for root, _, files in os.walk('templates'):
    for file in files:
        if file.endswith('.html'):
            FILES_TO_SCAN.append(os.path.join(root, file))

def extract_clean_keys(content):
    """
    Surgically parses keys by verifying authentic JavaScript function invocation boundaries,
    handling fallback arguments, and parsing HTML layout tokens cleanly.
    """
    extracted = set()
    length = len(content)
    idx = 0
    
    while idx < length:
        idx = content.find('t(', idx)
        if idx == -1:
            break
            
        # Strict boundary check: ensure t( is a separate function, not inside a word or style string
        if idx > 0 and (content[idx-1].isalnum() or content[idx-1] in ['_', '-', '.']):
            idx += 2
            continue
            
        start_pos = idx + 2
        bracket_depth = 1
        current_pos = start_pos
        
        while bracket_depth > 0 and current_pos < length:
            char = content[current_pos]
            if char == '(':
                bracket_depth += 1
            elif char == ')':
                bracket_depth -= 1
            current_pos += 1
            
        raw_args = content[start_pos:current_pos-1].strip()
        idx = current_pos
        
        if not raw_args:
            continue
            
        # Grab the first literal argument cleanly
        first_char = raw_args[0] if len(raw_args) > 0 else ''
        if first_char in ["'", '"', '`']:
            end_quote_idx = raw_args.find(first_char, 1)
            if end_quote_idx != -1:
                clean_key = raw_args[1:end_quote_idx]
            else:
                clean_key = raw_args.split(',')[0].strip("'\"` ")
        else:
            clean_key = raw_args.split(',')[0].strip("'\"` ")
            
        if clean_key:
            extracted.add(clean_key)

    # 2. Match HTML data attribute declarations
    for marker in ['data-i18n="', "data-i18n='"]:
        pos = 0
        while True:
            pos = content.find(marker, pos)
            if pos == -1:
                break
            start = pos + len(marker)
            quote = marker[-1]
            end = content.find(quote, start)
            if end != -1:
                val = content[start:end].strip()
                if val:
                    extracted.add(val)
            pos = start

    return extracted

def is_invalid_key(key):
    """Filters out CSS variables, template logic fragments, and programming markers."""
    if len(key) <= 1 or key.isdigit():
        return True
    if 'deg' in key or 'px' in key or key.startswith('#') or key.startswith('.') or key.endswith('fr'):
        return True
        
    bad_syntax = ['${', '?', ':', '||', '&&', '=', ';', '+', '/', '(', ')', '<', '>', '[', ']', '*']
    if any(symbol in key for symbol in bad_syntax):
        return True
        
    if any(key.startswith(p) for p in ['u.', 'item.', 'r.', 'c.', 'health.', 'asset.', 'goal.']):
        return True
    return False

def make_title_case_fallback(key):
    """Converts snake_case words into crisp readable titles if no reference is found."""
    words = key.replace('_', ' ').replace('-', ' ').split()
    return " ".join([w.capitalize() for w in words])

def main():
    discovered_keys = set()
    output_file = os.path.join('static/i18n', 'en1.json')
    master_file = os.path.join('static/i18n', 'en.json')
    
    # 1. READ EXISTING VALUES TO PROTECT YOUR TRANSLATIONS
    existing_translations = {}
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_translations = json.load(f)
        except Exception:
            pass

    # Read from en.json as secondary safety backup for messages or long values
    master_translations = {}
    if os.path.exists(master_file):
        try:
            with open(master_file, 'r', encoding='utf-8') as f:
                master_translations = json.load(f)
        except Exception:
            pass

    # 2. RUN EXTRACTION
    for path in FILES_TO_SCAN:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                file_text = f.read()
                tokens = extract_clean_keys(file_text)
                for token in tokens:
                    if not is_invalid_key(token):
                        discovered_keys.add(token)
        except Exception as e:
            print(f"[!] Error processing {path}: {e}")

    # 3. BUILD OUTPUT MAP WITHOUT LOSING DATA
    pristine_json = {}
    for key in sorted(discovered_keys):
        # A: Check existing en1.json first
        if key in existing_translations and existing_translations[key] != key:
            pristine_json[key] = existing_translations[key]
        # B: If missing from en1.json, try to inherit real message sentences from en.json
        elif key in master_translations:
            pristine_json[key] = master_translations[key]
        # C: Brand new keys default to beautifully spaced Title Case words
        else:
            pristine_json[key] = make_title_case_fallback(key)

    # WINDOWS FIX: Explicitly name exist_ok keyword argument
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(pristine_json, f, indent=4, ensure_ascii=False)
        
    print(f"[✓] Translation sync pipeline processed successfully.")
    print(f"[*] Total valid code keys loaded inside en1.json: {len(pristine_json)}")

if __name__ == "__main__":
    main()