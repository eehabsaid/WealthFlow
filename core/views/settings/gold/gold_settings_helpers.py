# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

"""Shared by gold_type_settings_views.py and gold_purity_settings_views.py —
both list endpoints seed their defaults on GET, so the helper lives here
rather than duplicated or owned by only one of the two modules.

NOTE: part of the settings/gold/ domain package. If this file grows past
~200 lines, split it further within this folder and update
core/views/settings/__init__.py accordingly."""

from core.models import GoldTypeSetting, GoldPuritySetting


def _seed_gold_settings_defaults():
    default_types = [
        ("Coins", 1),
        ("Bars", 2),
        ("Jewelry", 3),
    ]
    for name, order in default_types:
        GoldTypeSetting.objects.get_or_create(
            name=name,
            defaults={"is_active": True, "order": order},
        )

    default_purities = [
        ("24k", "24K", 0),
        ("22k", "22K", 0),
        ("21k", "21K", 0),
        ("18k", "18K", 0),
    ]
    for key, label, order in default_purities:
        GoldPuritySetting.objects.get_or_create(
            key=key,
            defaults={
                "label": label,
                "cashback_per_gram": 0,
                "is_active": True,
                "order": order,
            },
        )
