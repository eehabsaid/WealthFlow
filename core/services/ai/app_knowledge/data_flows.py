"""Code-derived "how data flows" knowledge (ai_knowledge/10_data_flows.md).

Every name, list and yes/no below is read from the real code (constants, model choices, service
constants, the balance rule functions), not typed by hand, so the file cannot drift: a test compares
the committed file with build_data_flows_markdown(). Regenerate: python manage.py generate_ai_knowledge.
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings

FILE_NAME = "10_data_flows.md"


def _yes(flag: bool) -> str:
    return "yes" if flag else "no"


def _expense_rules() -> list[str]:
    from core.models import Expense
    from core.services.expenses.expense_balance_helpers import _expense_affects_balance, _expense_requires_bank

    methods = [value for value, _ in Expense._meta.get_field("payment_method").choices]
    return [f"- Expense payment method '{m}': deducts a balance entry: {_yes(_expense_affects_balance(m))}; "
            f"needs a bank account: {_yes(_expense_requires_bank(m))}" for m in methods]


def _asset_payment_rules() -> list[str]:
    from core.models import AssetPurchasePayment
    from core.services.fixed_assets.asset_purchase_service import _asset_payment_requires_bank

    methods = [value for value, _ in AssetPurchasePayment._meta.get_field("payment_method").choices]
    return [f"- Asset purchase payment method '{m}': needs a bank account: {_yes(_asset_payment_requires_bank(m))}" for m in methods]


def _asset_type_lines() -> list[str]:
    from core.constants import ASSET_TYPES, REAL_ESTATE_ASSET_TYPES
    from core.models import OtherAssetDetails

    other_fields = [f.name for f in OtherAssetDetails._meta.get_fields()
                    if f.concrete and not f.primary_key and f.name not in {"asset", "created_at", "updated_at"}]
    lines = [f"- Asset types (Fixed Assets page): {', '.join(v for v, _ in ASSET_TYPES)}."]
    lines.append(f"- Acquisition costs, renovations and furniture are kept only for type(s): {', '.join(sorted(REAL_ESTATE_ASSET_TYPES))}; "
                 "for every other type they are discarded on save.")
    lines.append(f"- 'Other Assets' details fields: {', '.join(other_fields)}.")
    return lines


def _mirror_lines() -> list[str]:
    from core.models.expenses import EXPENSE_SOURCE_TYPE_CHOICES
    from core.services.balance.card_renewal_fee_mirror_service import CARD_FEE_CATEGORY_NAME, CARD_FEE_SUBCATEGORY_NAME
    from core.services.balance.credit_card_payment_mirror_service import CREDIT_CARD_CATEGORY_NAME, CREDIT_CARD_SUBCATEGORY_NAME
    from core.services.fixed_assets.asset_expense_mirror_service import FIXED_ASSETS_CATEGORY_NAME, SUBCATEGORY_NAME_BY_SOURCE

    lines = ["- System-generated Expense rows (is_system_generated, read-only, source_type set) exist only for: "
             + ", ".join(f"{label} ({key})" for key, label in EXPENSE_SOURCE_TYPE_CHOICES) + "."]
    lines.append(f"- Fixed-asset mirrors land in expense category '{FIXED_ASSETS_CATEGORY_NAME}', subcategories: "
                 + ", ".join(SUBCATEGORY_NAME_BY_SOURCE.values()) + ".")
    lines.append(f"- Credit card payments land in '{CREDIT_CARD_CATEGORY_NAME}' / '{CREDIT_CARD_SUBCATEGORY_NAME}'; "
                 f"card renewal fees in '{CARD_FEE_CATEGORY_NAME}' / '{CARD_FEE_SUBCATEGORY_NAME}'.")
    lines.append("- A mirror row is edited or deleted from its source record, never from the Expenses page.")
    return lines


def build_data_flows_markdown() -> str:
    parts = [
        "# How data flows (generated from code - do not edit by hand)",
        "",
        "## Fixed assets",
        *_asset_type_lines(),
        "- Saving an asset with a purchase price records purchase payments; each payment deducts a cash/bank balance entry "
        "(same currency, same bank) and fails if that balance would go negative. Deleting the asset or editing the payments reverses it.",
        "- The asset purchase price itself is NOT written as an Expense row; only acquisition costs, renovations and furniture "
        "of a Real Estate asset are mirrored into Expenses.",
        "- Net worth counts each owned asset at its current market value (real estate, vehicles, other assets, gold).",
        *_asset_payment_rules(),
        "",
        "## Expenses",
        "- Saving an Expense deducts a balance entry when its payment method affects balance; editing or deleting reverses it.",
        *_expense_rules(),
        "- Expenses reduce cash and appear in spending analytics; they do not create or change any asset.",
        "",
        "## Mirroring (shared engine: core/services/shared/expense_mirror_engine.py)",
        *_mirror_lines(),
        "",
        "## Double counting",
        "- An Expense and an asset purchase payment each deduct a balance entry independently, so recording the same purchase "
        "in both deducts the money twice. Mirrored rows are the exception: they are created from the source record and do "
        "not deduct a second time.",
        "",
    ]
    return "\n".join(parts)


def data_flows_path() -> Path:
    return Path(settings.BASE_DIR) / "ai_knowledge" / FILE_NAME


def write_data_flows() -> Path:
    path = data_flows_path()
    path.write_text(build_data_flows_markdown(), encoding="utf-8", newline="\n")
    return path
