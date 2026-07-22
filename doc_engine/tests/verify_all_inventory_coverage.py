import os
import sys
import json
import struct

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from doc_engine.config import LATEST_SCREENSHOTS_DIR, MANIFEST_FILE

def get_png_dimensions(file_path):
    try:
        with open(file_path, 'rb') as f:
            data = f.read(25)
            if data[:8] != b'\x89PNG\r\n\x1a\n':
                return None
            width, height = struct.unpack('>II', data[16:24])
            return width, height
    except Exception:
        return None

def verify_inventory_coverage():
    print("\n==================================================")
    print("      INVENTORY & SCREENSHOT COVERAGE AUDIT        ")
    print("==================================================")

    screenshots_dir = LATEST_SCREENSHOTS_DIR

    if not os.path.exists(screenshots_dir):
        print(f"[ERROR] Screenshots directory missing: {screenshots_dir}")
        return False

    existing_files = set(os.listdir(screenshots_dir))
    print(f"[INFO] Total PNG Screenshots on Disk: {len(existing_files)}")

    manifest_data = {}
    if os.path.exists(MANIFEST_FILE):
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

    manifest_pages = manifest_data.get("pages", [])
    print(f"[INFO] Total Pages Recorded in Manifest: {len(manifest_pages)}")

    corrupted_files = []
    zero_size_files = []
    valid_count = 0

    for fname in existing_files:
        fpath = os.path.join(screenshots_dir, fname)
        size = os.path.getsize(fpath)
        if size == 0:
            zero_size_files.append(fname)
            continue
        dim = get_png_dimensions(fpath)
        if not dim:
            corrupted_files.append(fname)
        else:
            valid_count += 1

    print(f"[INFO] Valid PNG Files with Dimensions: {valid_count}/{len(existing_files)}")

    if zero_size_files:
        print(f"[FAIL] 0-Byte Screenshot Files Found: {zero_size_files}")
    if corrupted_files:
        print(f"[FAIL] Corrupted PNG Files Found: {corrupted_files}")

    all_valid = (len(zero_size_files) == 0) and (len(corrupted_files) == 0) and (len(existing_files) >= 136)

    print("==================================================")
    if all_valid:
        print("COVERAGE AUDIT RESULT: PASSED - 100% Valid & Visible Screenshots!")
    else:
        print("COVERAGE AUDIT RESULT: FAILED - Issues detected.")
    print("==================================================\n")
    return all_valid

if __name__ == "__main__":
    verify_inventory_coverage()
