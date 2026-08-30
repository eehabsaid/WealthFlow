"""
fixed_assets_snapshot builder, split out of portfolio.py to stay under the
200-line limit. Pure function of portfolio_components() output.
"""
from __future__ import annotations


def build_fixed_assets_snapshot(comp: dict) -> dict:
    net_worth = comp["net_worth_egp"]
    fixed_total = comp["fixed_assets_total_egp"]
    liquid_total = comp["liquid_assets_total_egp"]

    fixed_ratio = (fixed_total / net_worth) * 100 if net_worth > 0 else 0
    liquid_ratio = (liquid_total / net_worth) * 100 if net_worth > 0 else 0

    fixed_breakdown = comp["fixed_assets"]
    fixed_breakdown_pct = {
        "type_real_estate": (fixed_breakdown["real_estate"] / fixed_total) * 100 if fixed_total > 0 else 0,
        "type_vehicles": (fixed_breakdown["vehicles"] / fixed_total) * 100 if fixed_total > 0 else 0,
        "type_other_assets": (fixed_breakdown["other_assets"] / fixed_total) * 100 if fixed_total > 0 else 0,
        "type_gold": (comp["gold_value_egp"] / net_worth) * 100 if net_worth > 0 else 0,
    }

    return {
        "total_fixed_assets_value": round(fixed_total, 2),
        "liquid_assets_value": round(liquid_total, 2),
        "total_net_worth": round(net_worth, 2),
        "fixed_assets_ratio": round(fixed_ratio, 2),
        "liquid_assets_ratio": round(liquid_ratio, 2),
        "net_worth_contribution": round(fixed_ratio, 2),
        "totalFixedAssetsValue": round(fixed_total, 2),
        "liquidAssetsValue": round(liquid_total, 2),
        "totalNetWorth": round(net_worth, 2),
        "fixedAssetsRatio": round(fixed_ratio, 2),
        "liquidAssetsRatio": round(liquid_ratio, 2),
        "netWorthContribution": round(fixed_ratio, 2),
        "fixed_assets_breakdown": {
            "type_real_estate": round(fixed_breakdown["real_estate"], 2),
            "type_vehicles": round(fixed_breakdown["vehicles"], 2),
            "type_other_assets": round(fixed_breakdown["other_assets"], 2),
        },
        "fixed_assets_breakdown_pct": {
            key: round(value, 2) for key, value in fixed_breakdown_pct.items()
        },
        "portfolio_distribution": {
            "liquid_assets": round(liquid_total, 2),
            "fixed_assets": round(fixed_total, 2),
        },
    }
