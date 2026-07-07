import os
import json

LANG_DIR = os.path.join('static', 'i18n')
# Included your root directory to catch Python backend modules/views dictionary lookups
SRC_DIRS = ['static/js', 'templates', 'apps', '.']  

def get_all_src_content():
    """Caches all project source files (.js, .html, .py) to track active keywords."""
    combined_content = ""
    for folder in SRC_DIRS:
        if not os.path.exists(folder):
            continue
        for root, _, files in os.walk(folder):
            # Skip virtual environments or cache tracks
            if 'venv' in root or '__pycache__' in root or '.git' in root:
                continue
            for file in files:
                if file.endswith(('.js', '.html', '.py')):
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            combined_content += f.read() + "\n"
                    except Exception as e:
                        pass
    return combined_content

def audit_and_isolate_unused():
    master_path = os.path.join(LANG_DIR, 'en.json')
    deleted_log_path = os.path.join(LANG_DIR, 'endeleted.json')
    
    if not os.path.exists(master_path):
        print(f"[!] Error: Master reference file 'en.json' not found at: {master_path}")
        return
        
    with open(master_path, 'r', encoding='utf-8') as f:
        master_translations = json.load(f)

    print(f"[*] Analyzing project files (including Python view dictionaries)...")
    codebase_payload = get_all_src_content()

    deleted_dictionary = {}
    for key, value in master_translations.items():
        clean_search_key = key.strip("'\"` ")
        
        # If the literal key tag is absent across your templates, scripts, and Python logic files
        if clean_search_key not in codebase_payload:
            deleted_dictionary[key] = value

    if deleted_dictionary:
        sorted_deleted = {k: deleted_dictionary[k] for k in sorted(deleted_dictionary.keys())}
        with open(deleted_log_path, 'w', encoding='utf-8') as f:
            json.dump(sorted_deleted, f, indent=4, ensure_ascii=False)
            
        print(f"[✓] Analysis complete! Found {len(deleted_dictionary)} completely unreferenced keys.")
        print(f"[+] Saved safely inside: {deleted_log_path}")
        print(f"[i] Safety Check: Your master 'en.json' remains 100% untouched.")
    else:
        print("[✓] Clean Scan Complete: Every single key in your reference file is actively utilized.")

if __name__ == "__main__":
    audit_and_isolate_unused()