"""Categories 5 and 6: fixed assets with their acquisition costs and renovations, and mortgages. Figures come from the owner's own rows
(FixedAsset, AssetAcquisitionCost, AssetRenovation, AssetMortgage); assets are named in the question only when the name is unique."""

from __future__ import annotations

from django.db.models import Sum

from core.services.shared.base_currency import get_user_base_code

from ..fam_util import dec, expand, money, nonzero, percent, rows, unique_names


def _assets(user):
    qs = rows(user, "FixedAsset")
    return (qs, unique_names(qs)) if qs is not None else (None, {})


def _sum(user, table, asset_id, field):
    qs = rows(user, table)
    return dec(qs.filter(asset_id=asset_id).aggregate(t=Sum(field))["t"]) if qs is not None else dec(0)


def train(user, langs, rng) -> list:
    qs, names, out = *_assets(user), []
    for aid, name in names.items():
        asset = qs.get(pk=aid)
        acq, ren = _sum(user, "AssetAcquisitionCost", aid, "amount_base"), _sum(user, "AssetRenovation", aid, "amount_base")
        if asset.purchase_price is not None and (acq or ren):
            total = dec(asset.purchase_price) + acq + ren
            out += expand(f"asset_invested:{aid}", "asset_invested", rng, langs, [money(total)], lambda l, n=name: {"asset": n}, category="cross", level="complex")
        if ren:
            out += expand(f"asset_renovations:{aid}", "asset_renovations", rng, langs, [money(ren)], lambda l, n=name: {"asset": n}, category="fixed_assets")
    mort = rows(user, "AssetMortgage")
    if mort is not None and mort.count() >= 2:
        total = dec(mort.aggregate(t=Sum("monthly_installment"))["t"])
        if nonzero([total]):
            out += expand("mortgage_monthly", "mortgage_monthly", rng, langs, [money(total)], lambda l: {"x": "y"}, category="liabilities")

    owned = qs.filter(status="Owned") if qs is not None else None
    mortgages = rows(user, "AssetMortgage")
    if owned is not None and mortgages is not None:
        for loan in mortgages.filter(asset__status="Owned").select_related("asset"):
            name = names.get(loan.asset_id)
            if not name or loan.asset.current_market_value is None:
                continue
            equity = dec(loan.asset.current_market_value) - dec(loan.remaining_balance)
            if nonzero([equity]):
                out += expand(
                    f"asset_equity:{loan.asset_id}", "asset_equity", rng, langs, [money(equity)],
                    lambda l, n=name: {"asset": n}, category="cross", level="complex",
                )
    return out


def evaluate(user, langs, rng) -> list:
    qs, names, out = *_assets(user), []
    for aid, name in names.items():
        asset = qs.get(pk=aid)
        if asset.purchase_price is not None and asset.current_market_value is not None:
            gain = dec(asset.current_market_value) - dec(asset.purchase_price)
            if nonzero([gain]):
                out += expand(f"asset_gain:{aid}", "asset_gain", rng, langs, [money(gain)], lambda l, n=name: {"asset": n}, category="fixed_assets", prefix="eval:")
        mort = rows(user, "AssetMortgage")
        loan = mort.filter(asset_id=aid).first() if mort is not None else None
        share = percent(dec(loan.loan_amount) - dec(loan.remaining_balance), loan.loan_amount) if loan else None
        if share and nonzero([share]):
            out += expand(f"mortgage_repaid:{aid}", "mortgage_repaid", rng, langs, [share], lambda l, n=name: {"asset": n}, category="liabilities", level="complex", prefix="eval:")

    furniture = rows(user, "AssetFurniture")
    if furniture is not None:
        groups = furniture.filter(asset__status="Owned").exclude(amount_base__isnull=True).values(
            "asset_id"
        ).annotate(total=Sum("amount_base"))
        for row in groups:
            name = names.get(row["asset_id"])
            total = dec(row["total"])
            if name and nonzero([total]):
                out += expand(
                    f"furniture_cost:{row['asset_id']}", "furniture_cost", rng, langs, [money(total)],
                    lambda l, n=name: {"asset": n}, category="fixed_assets", level="intermediate", prefix="eval:",
                )

    receipts = rows(user, "RentReceipt")
    base = str(get_user_base_code(user) or "").upper()
    if receipts is not None and names:
        groups = receipts.filter(currency__code__iexact=base, rental__asset__owner=user).values(
            "rental__asset_id", "received_date__year"
        ).annotate(total=Sum("amount"))
        for row in groups:
            name = names.get(row["rental__asset_id"])
            total = dec(row["total"])
            if name and nonzero([total]):
                out += expand(
                    f"rent_receipts_year:{row['rental__asset_id']}:{row['received_date__year']}",
                    "rent_receipts_year", rng, langs, [money(total)],
                    lambda l, n=name, y=row["received_date__year"], c=base: {"asset": n, "year": y, "currency": c},
                    category="income", level="intermediate", prefix="eval:",
                )
    return out
