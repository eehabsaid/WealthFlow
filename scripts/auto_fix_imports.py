import json
import os
import re
import subprocess

search_dirs = ["core/views/fixed_assets", "core/services/fixed_assets"]

def get_all_python_files():
    files = []
    for d in search_dirs:
        for root, _, filenames in os.walk(d):
            for filename in filenames:
                if filename.endswith(".py") and filename != "__init__.py":
                    files.append(os.path.join(root, filename))
    return files

def build_definition_map():
    definition_map = {}
    pattern = re.compile(r"^(?:async\s+)?def\s+([_a-zA-Z0-9]+)\s*\(")
    class_pattern = re.compile(r"^class\s+([_a-zA-Z0-9]+)\s*(\(|:)")
    for filepath in get_all_python_files():
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                match = pattern.match(line)
                if match:
                    func_name = match.group(1)
                    definition_map[func_name] = filepath
                match_class = class_pattern.match(line)
                if match_class:
                    class_name = match_class.group(1)
                    definition_map[class_name] = filepath
    return definition_map

def main():
    print("Running ruff...")
    result = subprocess.run(
        [r".\venv\Scripts\ruff.exe", "check", "--output-format", "json"] + search_dirs,
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    
    try:
        errors = json.loads(result.stdout)
    except Exception as e:
        print("Could not parse ruff output:")
        print(result.stdout[:500])
        raise e

    definition_map = build_definition_map()

    # file_to_missing -> {file_path: {module_path: set(names)}}
    file_to_missing = {}

    for error in errors:
        if error["code"] == "F821" and "Undefined name" in error["message"]:
            msg = error["message"]
            match = re.search(r"[`']([^`']+)[`']", msg)
            if not match:
                continue
            name = match.group(1)
            # ruff json gives absolute paths or relative paths. Normalize to use /
            filepath = error["filename"].replace("\\", "/")
            # find matching local relative path
            for d in search_dirs:
                idx = filepath.find(d)
                if idx != -1:
                    filepath = filepath[idx:]
                    break

            if name in definition_map:
                source_file = definition_map[name]
                if source_file == filepath:
                    continue 
                
                module_path = source_file.replace("\\", "/").replace(".py", "").replace("/", ".")
                
                if filepath not in file_to_missing:
                    file_to_missing[filepath] = {}
                if module_path not in file_to_missing[filepath]:
                    file_to_missing[filepath][module_path] = set()
                file_to_missing[filepath][module_path].add(name)
            else:
                print(f"Could not find definition for {name} missing in {filepath}")

    for filepath, missing_modules in file_to_missing.items():
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        import_statements = []
        for mod, names in missing_modules.items():
            import_statements.append(f"from {mod} import {', '.join(sorted(names))}")
        
        lines = content.split('\n')
        last_import_line = 0
        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                last_import_line = i

        lines.insert(last_import_line + 1, "\n" + "\n".join(import_statements) + "\n")
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write('\n'.join(lines))
        print(f"Fixed {filepath}")

if __name__ == "__main__":
    main()
