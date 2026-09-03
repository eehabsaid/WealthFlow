from datetime import date, datetime


def _date_to_iso(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if value:
        return str(value)
    return ""
