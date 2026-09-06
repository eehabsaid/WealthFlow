class InsightsMixin:
    """AI insight and recommendation generation from category and monthly data."""

    def _build_insights(self, months, categories):
        insights = []

        if len(months) >= 2:
            last_month = months[-1]
            prev_month = months[-2]
            if prev_month["total_egp"] > 0:
                diff_pct = ((last_month["total_egp"] - prev_month["total_egp"]) / prev_month["total_egp"]) * 100.0

                if diff_pct > 15:
                    insights.append({
                        "key": "spending_intelligence_insight_increased",
                        "params": {"pct": str(round(diff_pct, 1))}
                    })
                elif diff_pct < -15:
                    insights.append({
                        "key": "spending_intelligence_insight_decreased",
                        "params": {"pct": str(round(abs(diff_pct), 1))}
                    })

        if len(categories) > 0:
            top_cat = categories[0]
            if top_cat["percentage"] > 40:
                insights.append({
                    "key": "spending_intelligence_insight_dominates",
                    "params": {"category": top_cat["name"], "pct": str(round(top_cat["percentage"], 1))}
                })

        return insights

    def _build_recommendations(self, months, categories):
        recommendations = []

        if len(categories) > 0:
            top_cat = categories[0]

            # Data-driven recommendations
            recommendations.append({
                "key": "spending_intelligence_rec_food_pct",
                "params": {"pct": str(round(top_cat["percentage"], 1)), "category": top_cat["name"]},
                "priority": "High" if top_cat["percentage"] > 30 else "Medium"
            })

            if len(categories) > 1:
                second_cat = categories[1]
                recommendations.append({
                    "key": "spending_intelligence_rec_family_largest",
                    "params": {"category": second_cat["name"]},
                    "priority": "Medium"
                })

        if len(months) >= 2:
            last_month = months[-1]
            prev_month = months[-2]
            if prev_month["total_egp"] > 0 and last_month["total_egp"] > prev_month["total_egp"]:
                diff_pct = ((last_month["total_egp"] - prev_month["total_egp"]) / prev_month["total_egp"]) * 100.0
                recommendations.append({
                    "key": "spending_intelligence_rec_transport_increased",
                    "params": {"pct": str(round(diff_pct, 1))},
                    "priority": "High" if diff_pct > 15 else "Medium"
                })

        if len(categories) >= 3 and categories[0]["percentage"] < 30:
            recommendations.append({
                "key": "spending_intelligence_rec_balanced",
                "params": {},
                "priority": "Low"
            })
        elif len(recommendations) < 3:
            # Add fallback recommendation
            recommendations.append({
                "key": "spending_intelligence_rec_discretionary",
                "params": {},
                "priority": "Low"
            })

        return recommendations
