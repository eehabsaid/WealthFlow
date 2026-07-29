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
