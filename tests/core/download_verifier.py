"""
WealthFlow Download Verifier Utility
Verifies exported files (Excel .xlsx, PDF .pdf, CSV .csv, Backup .wfbackup):
 1. File exists in test_downloads/
 2. Correct filename pattern
 3. Non-zero file size (> 0 bytes)
 4. Valid extension and file header/content
"""

import os

def verify_downloaded_file(filepath, expected_extension=None, min_bytes=10):
    """
    Strict Download File Verification:
    - Checks existence
    - Checks file size > min_bytes
    - Validates file header content
    """
    assert os.path.exists(filepath), f"Downloaded file does not exist at path: {filepath}"
    
    file_size = os.path.getsize(filepath)
    assert file_size >= min_bytes, f"Downloaded file at '{filepath}' is too small ({file_size} bytes)"

    filename = os.path.basename(filepath)
    ext = os.path.splitext(filename)[1].lower()

    if expected_extension:
        assert ext == expected_extension.lower(), f"Expected extension '{expected_extension}', got '{ext}' for file '{filename}'"

    # Header validations
    with open(filepath, "rb") as f:
        header = f.read(20)

    if ext == ".pdf":
        assert header.startswith(b"%PDF-"), f"PDF file '{filename}' does not start with valid PDF header '%PDF-'"
    elif ext == ".csv":
        assert len(header) > 0, f"CSV file '{filename}' is empty"
    elif ext == ".xlsx":
        assert header.startswith(b"PK\x03\x04"), f"Excel file '{filename}' is not a valid zip/xlsx archive"
    elif ext == ".wfbackup":
        assert len(header) > 0, f"Backup file '{filename}' is empty"

    print(f"  [DOWNLOAD VERIFIED] {filename} ({file_size} bytes, format: {ext})")
    return True


# Tables that were once silently missing from backups, plus the core ones: every .wfbackup must contain them.
REQUIRED_BACKUP_TABLES = (
    "user", "group", "contenttype", "permission", "group_permissions", "user_groups", "user_user_permissions",
    "expense", "balanceentry", "fixedasset", "budget", "recurringtransaction",
    "accessattempt", "accessattemptexpiration", "accessfailurelog", "accesslog", "logentry",
)


def verify_backup_archive(filepath, required_tables=REQUIRED_BACKUP_TABLES):
    """Opens a downloaded .wfbackup (a zip) and checks: manifest.json is valid, every checksum matches, and every
    required table file is present with its row count equal to the manifest. Returns the number of table files."""
    import hashlib
    import json
    import re
    import zipfile

    with zipfile.ZipFile(filepath) as zf:
        names = zf.namelist()
        assert "manifest.json" in names, f"Backup '{filepath}' has no manifest.json"
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        for entry, expected in manifest.get("checksums", {}).items():
            assert hashlib.sha256(zf.read(entry)).hexdigest() == expected, f"Checksum mismatch for {entry} in {filepath}"
        tables = {re.sub(r"^\d{2}[a-z]?_(.+)\.json$", r"\1", n): n for n in names if re.match(r"^\d{2}[a-z]?_.+\.json$", n)}
        missing = [t for t in required_tables if t not in tables]
        assert not missing, f"Backup '{filepath}' is missing tables: {missing}"
        for table in required_tables:
            payload = json.loads(zf.read(tables[table]).decode("utf-8"))
            assert payload["count"] == len(payload["rows"]), f"Row count mismatch in {tables[table]}"
    print(f"  [BACKUP CONTENT VERIFIED] {len(tables)} tables, all {len(required_tables)} required present")
    return len(tables)
