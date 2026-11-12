"""
Certificate -> Cash Balance principal deduction service (package).

Package layout (200-line file convention); this __init__ re-exports the
original module's public names so existing import paths keep working:
    errors.py    - exception classes
    matching.py  - balance entry lookup, validation, apply_delta
    handlers.py  - pre_save / post_save / pre_delete handlers

Behaviour:
  1. Target balance entry is matched by bank_id + currency_id, restricted
     to BalanceEntry.balance_type == "cash" (case-insensitive).
  2. If no matching cash balance entry exists for a certificate's
     bank/currency, saving the certificate is BLOCKED with
     CertificateBalanceMappingError (raised in pre_save).
  3. A certificate "holds" its principal (deducted from cash) while its
     status is anything other than "Closed" (case-insensitive). A Closed
     certificate holds 0: its principal is returned to the cash balance.
  4. If the matching cash entry cannot cover the principal to be held,
     saving is BLOCKED with CertificateInsufficientBalanceError. On an
     update only the NET delta is checked (the old held principal is
     treated as available again). Closing or lowering the amount can never
     trigger this error; re-opening a closed certificate does re-check it.
  5. On every save the previously held principal is fully reversed and the
     current held principal re-applied (apply/reverse pattern):
       Active -> Closed  : principal returned to cash
       Closed -> Active  : principal deducted again
       amount/bank/currency edits net out to the correct delta.
     This covers both the manual close and the automatic maturity close
     (CertificateAutomationService.close_matured_certificates), since both
     are plain status saves.
  6. Deleting a certificate returns its held principal (nothing if Closed,
     as it was already returned).
  7. Does NOT touch the certificate-aggregate sync in
     core/models/certificate/balance_sync.py (balance_type "certificate").
  8. The view layer (core/views/certificate_views.py) maps the two errors to
     a JSON 400 {"error_code", "error"}; the frontend translates error_code.
"""

from .errors import CertificateBalanceMappingError, CertificateInsufficientBalanceError
from .handlers import (
    handle_certificate_post_save,
    handle_certificate_pre_delete,
    handle_certificate_pre_save,
)
from .matching import (
    apply_delta,
    find_cash_balance_entry,
    held_amount,
    is_principal_released,
    validate_balance_entry_exists,
    validate_sufficient_balance,
)

# Backward-compatible alias for the former private name.
_apply_delta = apply_delta

__all__ = [
    "CertificateBalanceMappingError",
    "CertificateInsufficientBalanceError",
    "apply_delta",
    "find_cash_balance_entry",
    "handle_certificate_post_save",
    "handle_certificate_pre_delete",
    "handle_certificate_pre_save",
    "held_amount",
    "is_principal_released",
    "validate_balance_entry_exists",
    "validate_sufficient_balance",
]
