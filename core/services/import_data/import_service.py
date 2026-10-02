"""Orchestrates the two-step CSV/Excel import flow:

1. preview(): parse the uploaded file, suggest a column mapping, and
   return every parsed row to the client (stateless — the browser holds
   the parsed rows and sends them straight back on confirm, so there is
   no server-side temp-file/session state to clean up).
2. confirm(): given the user-edited mapping + the same rows, detect
   duplicates against existing Expense rows, then create an Expense per
   remaining row via ExpenseService (which already handles
   currency-to-base conversion — no separate conversion logic here).
"""
from core.services.import_data.column_mapper import (
    parse_amount_value,
    parse_date_value,
    suggest_mapping,
)
from core.services.import_data.duplicate_detector import find_duplicates
from core.services.import_data.parsers import parse_uploaded_file

MAX_PREVIEW_SAMPLE = 20


class ImportService:
    @staticmethod
    def preview(uploaded_file):
        headers, rows = parse_uploaded_file(uploaded_file)
        return {
            "headers": headers,
            "suggested_mapping": suggest_mapping(headers),
            "sample_rows": rows[:MAX_PREVIEW_SAMPLE],
            "rows": rows,
            "total_rows": len(rows),
        }

    @staticmethod
    def _normalize_rows(rows, mapping):
        """Apply the confirmed column mapping to raw parsed rows, returning
        a list of {date, amount, description, category_name, raw} plus a
        parallel list of per-row error messages (empty string = ok)."""
        normalized = []
        errors = []
        date_col = mapping.get("date")
        amount_col = mapping.get("amount")
        desc_col = mapping.get("description")
        category_col = mapping.get("category")
        for raw in rows:
            date_value = parse_date_value(raw.get(date_col, "")) if date_col else None
            amount_value = parse_amount_value(raw.get(amount_col, "")) if amount_col else None
            description = (raw.get(desc_col, "") if desc_col else "").strip()
            category_name = (raw.get(category_col, "") if category_col else "").strip()
            if not date_value:
                errors.append("invalid_or_missing_date")
            elif amount_value is None or amount_value == 0:
                errors.append("invalid_or_missing_amount")
            else:
                errors.append("")
            normalized.append({
                "date": date_value,
                "amount": amount_value,
                "description": description,
                "category_name": category_name,
                "raw": raw,
            })
        return normalized, errors

    @staticmethod
    def confirm(owner, rows, mapping, currency_id=None, category_id=None, payment_method="Cash", skip_duplicates=True):
        from core.services.expenses.expense_service import ExpenseService

        normalized, row_errors = ImportService._normalize_rows(rows, mapping)
        duplicate_indices = find_duplicates(owner, normalized) if skip_duplicates else set()

        created = []
        skipped_duplicates = []
        errors = []
        for idx, row in enumerate(normalized):
            if row_errors[idx]:
                errors.append({"row": idx, "reason": row_errors[idx]})
                continue
            if idx in duplicate_indices:
                skipped_duplicates.append(idx)
                continue
            try:
                expense = ExpenseService.create_expense(
                    {
                        "date": row["date"].isoformat(),
                        "category_id": category_id,
                        "description": row["description"] or row["category_name"] or "Imported transaction",
                        "amount": row["amount"],
                        "currency_id": currency_id,
                        "payment_method": payment_method,
                        "notes": "Imported from file",
                    },
                    owner,
                )
            except ValueError as exc:
                errors.append({"row": idx, "reason": str(exc)})
                continue
            created.append(expense)

        return {
            "created_count": len(created),
            "created": [e.to_dict() for e in created],
            "skipped_duplicate_count": len(skipped_duplicates),
            "error_count": len(errors),
            "errors": errors,
        }
