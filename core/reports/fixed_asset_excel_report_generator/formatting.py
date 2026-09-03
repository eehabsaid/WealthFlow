import io

from django.http import HttpResponse


def autofit_columns(wb):
    for ws in wb.worksheets:
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    max_length = max(max_length, len(str(cell.value or "")))
                except Exception:
                    pass
            ws.column_dimensions[column].width = min(max_length + 2, 40)


def build_xlsx_response(wb, assets, scope):
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = (
        f"fixed_asset_{assets[0].id}_report.xlsx"
        if scope == "single"
        else "fixed_assets_portfolio_report.xlsx"
    )
    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
