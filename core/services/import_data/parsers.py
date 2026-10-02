"""Parse an uploaded CSV or Excel file into a plain list-of-dicts, keyed
by the file's own header row. No currency or amount interpretation here
— that's column_mapper.py's job, once the user confirms which column
means what.
"""
import csv
import io

MAX_IMPORT_ROWS = 5000


class UnsupportedFileTypeError(ValueError):
    pass


class EmptyFileError(ValueError):
    pass


def parse_uploaded_file(uploaded_file):
    """Return (headers: list[str], rows: list[dict]) from a Django
    UploadedFile. Supports .csv and .xlsx/.xls (via openpyxl)."""
    name = (uploaded_file.name or "").lower()
    if name.endswith(".csv") or name.endswith(".txt"):
        return _parse_csv(uploaded_file)
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return _parse_excel(uploaded_file)
    raise UnsupportedFileTypeError("unsupported_file_type")


def _parse_csv(uploaded_file):
    raw = uploaded_file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1256", errors="replace")  # common Arabic-Windows export encoding
    reader = csv.reader(io.StringIO(text))
    rows_raw = [r for r in reader if any(cell.strip() for cell in r)]
    if not rows_raw:
        raise EmptyFileError("empty_file")
    headers = [h.strip() for h in rows_raw[0]]
    rows = []
    for r in rows_raw[1 : MAX_IMPORT_ROWS + 1]:
        row = {headers[i]: (r[i].strip() if i < len(r) else "") for i in range(len(headers))}
        rows.append(row)
    return headers, rows


def _parse_excel(uploaded_file):
    from openpyxl import load_workbook

    wb = load_workbook(filename=io.BytesIO(uploaded_file.read()), read_only=True, data_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    try:
        header_row = next(rows_iter)
    except StopIteration:
        raise EmptyFileError("empty_file") from None
    headers = [str(h).strip() if h is not None else "" for h in header_row]
    rows = []
    for i, r in enumerate(rows_iter):
        if i >= MAX_IMPORT_ROWS:
            break
        if r is None or all(cell in (None, "") for cell in r):
            continue
        row = {}
        for j, h in enumerate(headers):
            value = r[j] if j < len(r) else ""
            row[h] = "" if value is None else str(value).strip()
        rows.append(row)
    if not rows and not headers:
        raise EmptyFileError("empty_file")
    return headers, rows
