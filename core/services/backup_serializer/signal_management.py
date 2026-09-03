"""
Signal disconnection/reconnection around bulk restore, and the post-restore
balance-sync sweep.
"""

from __future__ import annotations


def disconnect_restore_signals():
    """
    Disconnect all signals that perform automatic balance syncing.
    Call this before bulk-importing records during a restore.
    """
    from django.db.models.signals import post_delete, post_save, pre_save

    from core.models.certificate import (
        BankCertificate,
        handle_certificate_delete,
        handle_certificate_save,
    )
    from core.models.fixed_assets_history import (
        AssetSale,
        handle_asset_sale_delete,
        handle_asset_sale_pre_save,
        handle_asset_sale_save,
    )
    from core.models.fixed_assets_realestate import (
        AssetMortgage,
        AssetRental,
        handle_asset_mortgage_delete,
        handle_asset_mortgage_save,
        handle_asset_rental_delete,
        handle_asset_rental_save,
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
        from core.models.fixed_assets_history import AssetSale
        from core.models.fixed_assets_realestate import AssetMortgage, AssetRental
        from core.services.balance.financial_sync_service import FinancialSyncService
        svc = FinancialSyncService()
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
