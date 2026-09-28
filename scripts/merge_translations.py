import argparse
import json
import os

def deep_merge(dict1, dict2):
    """
    Recursively merge two dictionaries.
    - Preserves all keys from dict1.
    - Adds new keys from dict2.
    - Recursively merges nested dictionaries so nested keys aren't lost.
    - For conflicting leaf keys, dict2 takes precedence (newer version).
    """
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result:
            if isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = deep_merge(result[key], value)
            else:
                # Conflict: dict2 takes precedence as the newer version
                result[key] = value
        else:
            # Key only exists in dict2
            result[key] = value
    return result

def merge_translation_files(file1_path, file2_path, output_path):
    # Load both JSON files with UTF-8 encoding for Arabic support
    with open(file1_path, 'r', encoding='utf-8') as f1:
        data1 = json.load(f1)
    
    with open(file2_path, 'r', encoding='utf-8') as f2:
        data2 = json.load(f2)
    
    # Perform the deep merge
    merged_data = deep_merge(data1, data2)
    
    # Save the merged result with UTF-8 and ensure_ascii=False to preserve Arabic text cleanly
    with open(output_path, 'w', encoding='utf-8') as f_out:
        json.dump(merged_data, f_out, ensure_ascii=False, indent=4)
    
    print(f"Successfully merged:\n  - {file1_path}\n  - {file2_path}\nInto:\n  - {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge two JSON translation files containing Arabic recursively.")
    parser.add_argument("file1", help="Path to the first JSON translation file")
    parser.add_argument("file2", help="Path to the second JSON translation file (takes precedence on conflicts)")
    parser.add_argument("output", help="Path where the merged JSON file should be saved")
    
    args = parser.parse_args()
    
    merge_translation_files(args.file1, args.file2, args.output)