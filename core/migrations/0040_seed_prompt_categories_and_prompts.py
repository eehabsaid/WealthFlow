from django.db import migrations


def seed_prompt_categories_and_prompts(apps, schema_editor):
    AIPromptCategory = apps.get_model("core", "AIPromptCategory")
    AIPrompt = apps.get_model("core", "AIPrompt")

    categories_data = [
        {
            "code": "financial_analysis",
            "name": "Financial Analysis & Ratios",
            "description": "Prompts for deep portfolio evaluation, liquid balance ratios, and net worth audits.",
            "icon": "bi-graph-up",
            "display_order": 1,
        },
        {
            "code": "reporting",
            "name": "Executive & Wealth Reporting",
            "description": "Prompts for generating structured financial summaries, executive reports, and forecasts.",
            "icon": "bi-file-earmark-text",
            "display_order": 2,
        },
        {
            "code": "budgeting",
            "name": "Budget & Expense Optimization",
            "description": "Prompts for identifying expenditure trends and optimizing monthly cash flow.",
            "icon": "bi-pie-chart",
            "display_order": 3,
        },
        {
            "code": "investment",
            "name": "Asset & Portfolio Strategy",
            "description": "Prompts for asset rebalancing, inflation defense, and investment scenario testing.",
            "icon": "bi-cash-coin",
            "display_order": 4,
        },
        {
            "code": "general",
            "name": "General AI Directives",
            "description": "General custom directives and flexible financial queries.",
            "icon": "bi-chat-quote",
            "display_order": 5,
        },
    ]

    cat_map = {}
    for cdata in categories_data:
        cat, _ = AIPromptCategory.objects.get_or_create(
            code=cdata["code"],
            defaults={
                "name": cdata["name"],
                "description": cdata["description"],
                "icon": cdata["icon"],
                "display_order": cdata["display_order"],
                "is_active": True,
            },
        )
        cat_map[cdata["code"]] = cat

    prompts_data = [
        {
            "name": "Wealth Portfolio Audit",
            "category_code": "financial_analysis",
            "translation_key": "audit",
            "description": "Comprehensive audit of liquid, gold, real estate, and fixed income assets.",
            "content": "Analyze my current portfolio breakdown across liquid bank deposits, certificates, gold, and real estate assets. Highlight asset concentration risks, currency exposure, and liquidity coverage.",
            "is_favorite": True,
            "display_order": 1,
        },
        {
            "name": "Expense Reduction Strategy",
            "category_code": "budgeting",
            "translation_key": "expense",
            "description": "Identifies top spending categories and suggests monthly cost optimizations.",
            "content": "Review my recent monthly expense entries across categories. Identify top expenditure drivers, potential waste or non-essential spending, and actionable strategies to increase monthly net savings.",
            "is_favorite": True,
            "display_order": 2,
        },
        {
            "name": "Cash Flow & Maturity Forecast",
            "category_code": "reporting",
            "translation_key": "cashflow",
            "description": "Forecasts upcoming certificate interest payouts and maturity reinvestments.",
            "content": "Generate a cash flow outlook for the next 12 months based on active bank certificate interest schedules, salary income, and recurring expense obligations.",
            "is_favorite": False,
            "display_order": 3,
        },
        {
            "name": "Asset Rebalancing & Inflation Protection",
            "category_code": "investment",
            "translation_key": "rebalance",
            "description": "Provides rebalancing recommendations to protect wealth against inflation.",
            "content": "Assess the purchasing power defense of my total wealth. Evaluate the balance between gold holdings, interest-bearing certificates, and real estate assets relative to current inflation trends.",
            "is_favorite": False,
            "display_order": 4,
        },
        {
            "name": "Monthly Executive Wealth Summary",
            "category_code": "reporting",
            "translation_key": "execsum",
            "description": "Generates a formal executive summary of net worth changes and key financial milestones.",
            "content": "Create a concise executive summary of my total net worth, month-over-month wealth growth, key portfolio highlights, and strategic recommendations for next month.",
            "is_favorite": True,
            "display_order": 5,
        },
    ]

    for pdata in prompts_data:
        cat = cat_map.get(pdata["category_code"])
        if cat:
            AIPrompt.objects.get_or_create(
                name=pdata["name"],
                defaults={
                    "category": cat,
                    "translation_key": pdata["translation_key"],
                    "description": pdata["description"],
                    "content": pdata["content"],
                    "is_favorite": pdata["is_favorite"],
                    "display_order": pdata["display_order"],
                    "is_active": True,
                },
            )



def reverse_seed(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0039_aipromptcategory_aiprompt"),
    ]

    operations = [
        migrations.RunPython(seed_prompt_categories_and_prompts, reverse_seed),
    ]
