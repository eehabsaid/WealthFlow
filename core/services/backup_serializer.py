"""
backup_serializer.py
====================
Core serialisation / deserialisation helpers for the WealthFlow backup &
restore system.

Key responsibilities
--------------------
- Encode any Django field value to a JSON-safe primitive.
- Decode those primitives back to the correct Python types on restore.
- Provide MODEL_EXPORT_ORDER – the canonical, dependency-safe list of every
  model that should be backed-up / restored.
- Provide helpers for suppressing Django signals during bulk restore.

Special-data guarantees
-----------------------
Arabic / Unicode  → JSON written with ensure_ascii=False; no data is mutated.
DateField         → Always serialised as "YYYY-MM-DD" (ISO 8601).
DateTimeField     → Always serialised as "YYYY-MM-DDTHH:MM:SS+TZ" (ISO 8601).
DecimalField      → Serialised as a decimal string ("12345.67") to avoid IEEE
                     754 rounding.
BinaryField       → Base64-encoded ASCII string.
GenericForeignKey → content_type stored as "app_label.model_name" label.
User FKs          → User records are keyed by username on restore so integer
                     PKs do not need to match.
"""

from __future__ import annotations

import base64
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from django.contrib.contenttypes.models import ContentType

# ---------------------------------------------------------------------------
# Field-level serialise / deserialise
# ---------------------------------------------------------------------------

def serialize_value(value: Any) -> Any:
    """Convert a Python / Django field value to a JSON-safe primitive."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()          # "2025-03-15T10:30:00+00:00"
    if isinstance(value, date):
        return value.isoformat()          # "2025-03-15"
    if isinstance(value, Decimal):
        return str(value)                 # "12345.6700" – lossless
    if isinstance(value, (bytes, memoryview)):
        raw = bytes(value) if isinstance(value, memoryview) else value
        return base64.b64encode(raw).decode("ascii")
    # Everything else (str, int, float, bool, list, dict) is already JSON-safe
    return value


def deserialize_date(raw: str | None) -> date | None:
    """Parse an ISO date string back to a date object."""
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except (ValueError, TypeError):
        return None


def deserialize_datetime(raw: str | None) -> datetime | None:
    """Parse an ISO datetime string back to a datetime object."""
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except (ValueError, TypeError):
        return None


def deserialize_decimal(raw: str | None) -> Decimal:
    """Parse a decimal string back to Decimal. Returns 0 on failure."""
    if raw is None:
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except (InvalidOperation, TypeError):
        return Decimal("0")


def deserialize_binary(raw: str | None) -> bytes | None:
    """Decode a Base64 string back to bytes."""
    if raw is None:
        return None
    try:
        return base64.b64decode(raw.encode("ascii"))
    except Exception:
        return None


def resolve_content_type(label: str | None) -> ContentType | None:
    """
    Resolve an "app_label.model_name" string to a ContentType instance.
    Returns None if the label is empty or the ContentType does not exist.
    """
    if not label:
        return None
    try:
        app_label, model_name = label.split(".", 1)
        return ContentType.objects.get(app_label=app_label, model=model_name)
    except (ValueError, ContentType.DoesNotExist):
        return None


def content_type_label(ct: ContentType | None) -> str | None:
    """Return "app_label.model_name" string for a ContentType instance."""
    if ct is None:
        return None
    return f"{ct.app_label}.{ct.model}"


# ---------------------------------------------------------------------------
# MODEL_EXPORT_ORDER
# ---------------------------------------------------------------------------
# Each entry is a tuple:
#   (file_prefix, ModelClass, lookup_field_or_None)
#
# • file_prefix    – two-digit number used as the filename prefix in the ZIP
#                    archive. Lower numbers are imported first, ensuring FK
#                    parents always exist before their children.
# • ModelClass     – the Django model class to export.
# • lookup_field   – the field name used for update_or_create matching on
#                    restore. None = use 'pk'.
#
# Dependencies are ordered so that every FK target appears before the model
# that references it (leaves last).
# ---------------------------------------------------------------------------

def get_model_export_order():
    """
    Return MODEL_EXPORT_ORDER at call-time to avoid import-time circular
    dependencies.  Models are imported here so that Django's app registry is
    guaranteed to be ready.
    """
    from django.contrib.auth.models import User, Group

    from core.models import (
        Currency, Bank, Company,
        UserProfile, AuthToken, AuthAuditLog,
        PagePermission,
        AppSettings, EmailTemplate,
        BalanceEntry, BalanceTransfer, CurrencyExchange,
        ExchangeRate,
        SalaryEntry, PerDiem,
        BankCertificate, BankCertificateInterestHistory, CertificateStatus,
        GoldPrice, GoldPriceHistory, GoldTypeSetting, GoldPuritySetting,
        ExpenseCategory, ExpenseSubcategory, Expense,
        ReminderRule, ReminderLog,
        Goal,
        FixedAsset,
        RealEstateDetails, AssetMortgage, AssetRental,
        VehicleDetails, AssetMaintenance, AssetInsurance,
        GoldDetails,
        OtherAssetDetails,
        AssetRenovation, AssetFurniture,
        AssetValuationHistory, AssetPurchasePayment, AssetSale,
        Document,
        AssetPhoto,
    )

    return [
        # ── Django built-ins ───────────────────────────────────────────────
        ("01", Group,                        "name"),
        ("02", User,                         "username"),
        # ── Reference / lookup tables (no FKs to app models) ─────────────
        ("03", Currency,                     "code"),
        ("04", Bank,                         None),    # no natural key
        ("05", Company,                      None),
        ("06", CertificateStatus,            "name"),
        ("07", GoldTypeSetting,              "name"),
        ("08", GoldPuritySetting,            "key"),
        ("09", AppSettings,                  "key"),
        ("10", EmailTemplate,                "key"),
        # ── User-linked data ──────────────────────────────────────────────
        ("11", UserProfile,                  "user_id"),    # FK → User (1-to-1)
        ("12", AuthToken,                    None),
        ("13", AuthAuditLog,                 None),
        ("14", PagePermission,               None),
        # ── Financial core ────────────────────────────────────────────────
        ("15", BalanceEntry,                 None),
        ("16", BalanceTransfer,              None),
        ("16b", CurrencyExchange,             None),
        ("17", ExchangeRate,                 None),
        # ── Income / salary ───────────────────────────────────────────────
        ("18", SalaryEntry,                  None),
        ("19", PerDiem,                      None),
        # ── Bank certificates ─────────────────────────────────────────────
        ("20", BankCertificate,              None),
        ("21", BankCertificateInterestHistory, None),
        # ── Gold market data ──────────────────────────────────────────────
        ("22", GoldPrice,                    None),
        ("23", GoldPriceHistory,             None),
        # ── Expenses ──────────────────────────────────────────────────────
        ("24", ExpenseCategory,              "name"),
        ("25", ExpenseSubcategory,           None),
        ("26", Expense,                      None),
        # ── Reminders ─────────────────────────────────────────────────────
        ("27", ReminderRule,                 None),
        ("28", ReminderLog,                  None),
        # ── Goals ─────────────────────────────────────────────────────────
        ("29", Goal,                         None),
        # ── Fixed assets (parent first, then sub-types, then children) ───
        ("30", FixedAsset,                   None),
        ("31", RealEstateDetails,            "asset_id"),
        ("32", AssetMortgage,                "asset_id"),
        ("33", AssetRental,                  "asset_id"),
        ("34", VehicleDetails,               "asset_id"),
        ("35", AssetMaintenance,             None),
        ("36", AssetInsurance,               None),
        ("37", GoldDetails,                  "asset_id"),
        ("38", OtherAssetDetails,            "asset_id"),
        ("39", AssetRenovation,              None),
        ("40", AssetFurniture,               None),
        ("41", AssetValuationHistory,        None),
        ("42", AssetPurchasePayment,         None),
        ("43", AssetSale,                    "asset_id"),
        # ── Binary / media ────────────────────────────────────────────────
        ("44", Document,                     None),
        ("45", AssetPhoto,                   None),
    ]


# ---------------------------------------------------------------------------
# Signal management helpers
# ---------------------------------------------------------------------------

# Signals that cause side-effects during save – we disconnect them during
# restore and re-connect (and re-sync) afterwards.
_SIGNAL_REGISTRY: list[tuple] = []  # populated by disconnect_restore_signals()


def disconnect_restore_signals():
    """
    Disconnect all signals that perform automatic balance syncing.
    Call this before bulk-importing records during a restore.
    Returns a list of (signal, receiver_func, sender) tuples so they can be
    reconnected later.
    """
    from django.db.models.signals import post_save, post_delete, pre_save

    from core.models.certificate import (
        handle_certificate_save, handle_certificate_delete,
        BankCertificate,
    )
    from core.models.fixed_assets_history import (
        handle_asset_sale_pre_save, handle_asset_sale_save,
        handle_asset_sale_delete, AssetSale,
    )
    from core.models.fixed_assets_realestate import (
        handle_asset_mortgage_save, handle_asset_mortgage_delete, AssetMortgage,
        handle_asset_rental_save, handle_asset_rental_delete, AssetRental,
    )

    pairs = [
        (post_save,   handle_certificate_save,     BankCertificate),
        (post_delete, handle_certificate_delete,   BankCertificate),
        (pre_save,    handle_asset_sale_pre_save,  AssetSale),
        (post_save,   handle_asset_sale_save,      AssetSale),
        (post_delete, handle_asset_sale_delete,    AssetSale),
        (post_save,   handle_asset_mortgage_save,  AssetMortgage),
        (post_delete, handle_asset_mortgage_delete, AssetMortgage),
        (post_save,   handle_asset_rental_save,    AssetRental),
        (post_delete, handle_asset_rental_delete,  AssetRental),
    ]

    disconnected = []
    for signal, receiver_func, sender in pairs:
        result = signal.disconnect(receiver_func, sender=sender)
        if result:
            disconnected.append((signal, receiver_func, sender))

    return disconnected


def reconnect_signals(disconnected: list[tuple]):
    """Reconnect all signals that were previously disconnected."""
    for signal, receiver_func, sender in disconnected:
        signal.connect(receiver_func, sender=sender)


def run_post_restore_sync():
    """
    Run all balance synchronisation routines that should fire after a full
    restore is complete.
    """
    from core.models.certificate import sync_certificate_balance_entries
    sync_certificate_balance_entries()

    # Re-sync mortgage and rental balances (FinancialSyncService is idempotent)
    try:
        from core.services.balance.financial_sync_service import FinancialSyncService
        svc = FinancialSyncService()
        from core.models.fixed_assets_realestate import AssetMortgage, AssetRental
        from core.models.fixed_assets_history import AssetSale
        for obj in AssetMortgage.objects.select_related("asset").all():
            svc.sync_mortgage_balance(obj)
        for obj in AssetRental.objects.select_related("asset").all():
            svc.sync_rental_balance(obj)
        for obj in AssetSale.objects.select_related("asset").all():
            svc.sync_asset_sale_balance(obj)
    except Exception as exc:
        # FinancialSyncService is a best-effort post-restore step; log but
        # do not abort the restore.
        import logging
        logging.getLogger("wealthflow.backup").warning(
            "Post-restore FinancialSyncService failed: %s", exc
        )
