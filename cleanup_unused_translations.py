import os
import json

# Include directory roots to scan backend python modules (Views, Models dictionaries)
PROJECT_SRC_AREAS = ['static/js', 'templates', 'apps', '.']

def read_all_source_code():
    """Reads all project layers into memory to catch background dictionary keys."""
    combined_code = ""
    for folder in PROJECT_SRC_AREAS:
        if not os.path.exists(folder):
            continue
        for root, _, files in os.walk(folder):
            # Skip caches, standard configurations, and virtual environments
            if any(p in root for p in ['venv', '__pycache__', '.git', 'staticfiles']):
                continue
            for file in files:
                if file.endswith(('.js', '.html', '.py')):
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            combined_code += f.read() + "\n"
                    except:
                        pass
    return combined_code

def audit_unused_records():
    i18n_dir = os.path.join('static', 'i18n')
    base_target = os.path.join(i18n_dir, 'en1.json')
    log_output = os.path.join(i18n_dir, 'endeleted.json')
    
    if not os.path.exists(base_target):
        print(f"[!] Error: Ground target {base_target} missing. Run scan_translations.py first.")
        return

    with open(base_target, 'r', encoding='utf-8') as f:
        target_keys = json.load(f)

    print("[*] Compiling full project content matrix (JavaScript, HTML, Python)...")
    entire_source_code = read_all_source_code()

    isolated_unused = {}
    for key, value in target_keys.items():
        clean_key = key.strip("'\"` ")
        
        # If the key literal isn't referenced in templates, frontend scripts, or python models
        if clean_key not in entire_source_code:
            isolated_unused[key] = value

    if isolated_unused:
        sorted_unused = {k: isolated_unused[k] for k in sorted(isolated_unused.keys())}
        with open(log_output, 'w', encoding='utf-8') as f:
            json.dump(sorted_unused, f, indent=4, ensure_ascii=False)
        print(f"[✓] Verification Complete: Found {len(sorted_unused)} unused translation keys.")
        print(f"[+] Saved safely inside: {log_output}")
    else:
        print("[✓] Perfect! Every single scanned key is used somewhere in your codebase files.")

if __name__ == "__main__":
    audit_unused_records()