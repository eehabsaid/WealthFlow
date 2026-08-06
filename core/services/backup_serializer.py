"""
backup_serializer.py
====================
Core serialisation / deserialisation helpers for the WealthFlow backup &
restore system.
"""

from __future__ import annotations

import base64
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from django.contrib.contenttypes.models import ContentType

def serialize_value(value: Any) -> Any:
    """Convert a Python / Django field value to a JSON-safe primitive."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (bytes, memoryview)):
        raw = bytes(value) if isinstance(value, memoryview) else value
        return base64.b64encode(raw).decode("ascii")
    return value


def deserialize_date(raw: str | None) -> date | None:
    if not raw:
        return None
    if isinstance(raw, date):
        return raw
    try:
        return date.fromisoformat(raw[:10])
    except (ValueError, TypeError):
        return None


def deserialize_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    if isinstance(raw, datetime):
        return raw
    try:
        return datetime.fromisoformat(raw)
    except (ValueError, TypeError):
        return None


def deserialize_decimal(raw: Any, default: str = "0.00") -> Decimal:
    if raw is None:
        return Decimal(default)
    try:
        return Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def deserialize_binary(raw: str | None) -> bytes | None:
    if not raw:
        return None
    try:
        return base64.b64decode(raw.encode("ascii"))
    except Exception:
        return None


def resolve_content_type(label: str | None) -> ContentType | None:
    if not label:
        return None
    try:
        app_label, model_name = label.split(".", 1)
        return ContentType.objects.get(app_label=app_label, model=model_name)
    except (ValueError, ContentType.DoesNotExist):
        return None


def content_type_label(ct: ContentType | None) -> str | None:
    if ct is None:
        return None
    return f"{ct.app_label}.{ct.model}"


def get_model_export_order():
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
        GoldDetails, OtherAssetDetails,
        AssetRenovation, AssetFurniture,
        AssetValuationHistory, AssetPurchasePayment, AssetSale,
        Document, AssetPhoto,
        AIConversation, AIMessage, AIKnowledgeEntry, AIModelVersion, AIBenchmarkReport,
    )

    return [
        ("01", Group,                        "name"),
        ("02", User,                         "username"),
        ("03", Currency,                     "code"),
        ("04", Bank,                         None),
        ("05", Company,                      None),
        ("06", CertificateStatus,            "name"),
        ("07", GoldTypeSetting,              "name"),
        ("08", GoldPuritySetting,            "key"),
        ("09", AppSettings,                  "key"),
        ("10", EmailTemplate,                "key"),
        ("11", UserProfile,                  "user_id"),
        ("12", AuthToken,                    None),
        ("13", AuthAuditLog,                 None),
        ("14", PagePermission,               None),
        ("15", BalanceEntry,                 None),
        ("16", BalanceTransfer,              None),
        ("16b", CurrencyExchange,             None),
        ("17", ExchangeRate,                 None),
        ("18", SalaryEntry,                  None),
        ("19", PerDiem,                      None),
        ("20", BankCertificate,              None),
        ("21", BankCertificateInterestHistory, None),
        ("22", GoldPrice,                    None),
        ("23", GoldPriceHistory,             None),
        ("24", ExpenseCategory,              "name"),
        ("25", ExpenseSubcategory,           None),
        ("26", Expense,                      None),
        ("27", ReminderRule,                 None),
        ("28", ReminderLog,                  None),
        ("29", Goal,                         None),
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
        ("44", Document,                     None),
        ("45", AssetPhoto,                   None),
        ("46", AIConversation,               None),
        ("47", AIMessage,                    None),
        ("48", AIKnowledgeEntry,             "key"),
        ("49", AIModelVersion,               "version_name"),
        ("50", AIBenchmarkReport,            None),
    ]


# ---------------------------------------------------------------------------
# Signal management helpers
# ---------------------------------------------------------------------------

_SIGNAL_REGISTRY: list[tuple] = []


def disconnect_restore_signals():
    """
    Disconnect all signals that perform automatic balance syncing.
    Call this before bulk-importing records during a restore.
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
        import logging
        logging.getLogger("wealthflow.backup").warning(
            "Post-restore FinancialSyncService failed: %s", exc
        )
