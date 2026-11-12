"""Exceptions raised by the certificate -> cash balance sync."""

from django.core.exceptions import ValidationError


class CertificateBalanceMappingError(ValidationError):
    """Raised when no matching cash BalanceEntry exists for a certificate's
    bank + currency. Subclasses ValidationError so it behaves like a normal
    Django validation failure if a caller chooses to catch it that way."""
    error_code = "certificate_balance_mapping_missing"


class CertificateInsufficientBalanceError(ValidationError):
    """Raised when the matching cash BalanceEntry does not have enough
    funds to cover the certificate's held principal (net of any amount being
    freed up by reversing the certificate's previous deduction)."""
    error_code = "certificate_insufficient_balance"
