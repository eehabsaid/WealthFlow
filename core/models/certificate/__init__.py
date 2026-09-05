"""Umbrella re-export for every model + signal/sync helper in the
Certificate domain, so both core/models/__init__.py and any other file
can keep doing `from .certificate import BankCertificate` /
`from core.models.certificate import BankCertificate` unchanged, without
needing to know these moved from a flat core/models/certificate.py into
this package.

ORGANIZING PRINCIPLE: models and helpers that represent the Bank
Certificates page concept — the certificate record itself, its posted
interest history, the admin-configurable lifecycle statuses, and the
balance-sync signal machinery that keeps BalanceEntry in step with
active certificates.

STRUCTURE / CONVENTION:
  - bank_certificate.py      BankCertificate model.
  - interest_history.py      BankCertificateInterestHistory model.
  - certificate_status.py    CertificateStatus model.
  - balance_sync.py          _is_certificate_active, the pre_save/
                              post_save/pre_delete/post_delete signal
                              receivers, sync_certificate_balance_entries(),
                              and the internal _sync_certificate_balance()
                              helper that keeps BalanceEntry rows in sync.
  - core/services/backup_serializer/signal_management.py imports
    handle_certificate_save / handle_certificate_delete directly from
    `core.models.certificate` (this package), so those names must stay
    re-exported here even though nothing else at the models layer uses
    them directly.
  - Bank and Currency stay in core/models/ (flat) since they're shared
    reference data used well outside the Certificates domain.
  - If any file here grows past ~200 lines, split it by concern into
    more files in this same folder.
  - Always update this __init__.py's imports/__all__ to match.
"""

from core.models.certificate.bank_certificate import BankCertificate
from core.models.certificate.interest_history import BankCertificateInterestHistory
from core.models.certificate.certificate_status import CertificateStatus
from core.models.certificate.balance_sync import (
    _is_certificate_active,
    handle_certificate_balance_pre_save,
    handle_certificate_balance_post_save,
    handle_certificate_balance_pre_delete,
    handle_certificate_save,
    handle_certificate_delete,
    sync_certificate_balance_entries,
    _sync_certificate_balance,
)

__all__ = [
    "BankCertificate",
    "BankCertificateInterestHistory",
    "CertificateStatus",
    "_is_certificate_active",
    "handle_certificate_balance_pre_save",
    "handle_certificate_balance_post_save",
    "handle_certificate_balance_pre_delete",
    "handle_certificate_save",
    "handle_certificate_delete",
    "sync_certificate_balance_entries",
    "_sync_certificate_balance",
]
