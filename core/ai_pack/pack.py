"""The WealthFlow pack: registers the finance tools, providers, actions and training families with ai/."""
from core.ai_pack.host import base_currency  # noqa: F401  (re-exported for settings readers)

__all__ = ["base_currency"]


class _Advisor:
    """The financial-advisor services as the AI context builder sees them."""

    @staticmethod
    def available():
        from core.services.financial_advisor.registry import get_available_advisor_services
        return get_available_advisor_services()

    @staticmethod
    def payload(key, user):
        from core.services.financial_advisor.registry import get_financial_advisor_payload
        return get_financial_advisor_payload(key, user)


def _salary_enricher(res, user, query):
    if isinstance(res.get("salary"), dict):
        from core.ai_pack.tools.salary_answers import SALARY_INSTRUCTIONS, add_salary_answers
        add_salary_answers(res, user, query)
        res["instructions"] += SALARY_INSTRUCTIONS


def _category_names(user):
    from core.models import ExpenseCategory
    return ExpenseCategory.objects.filter(owner=user).values_list("name", flat=True)


def _data_slice(user, *args, **kwargs):
    from core.ai_pack.knowledge.data_slice import build_data_slice
    return build_data_slice(user, *args, **kwargs)


def _write_knowledge():
    from core.ai_pack.knowledge.data_flows import write_data_flows
    return write_data_flows()


def register(reg):
    from core.ai_pack.actions import expense, income, reminder
    from core.ai_pack.actions.tool import CHART_NAME, CHART_TOOL_DEF, NAME as ACTION_NAME, TOOL_DEF as ACTION_DEF
    from core.ai_pack.agents.advisor_agent import AdvisorAgent
    from core.ai_pack.tools.defs_scenario import SCENARIO_TOOL_DEFS
    from core.ai_pack.tools.defs_whatif import WHATIF_TOOL_DEFS
    from core.ai_pack.tools.validation_rules import _business_rules, _validate_tool_specific_params
    from core.ai_pack.training_families import assets, banking, budget, income as income_family, overview, whatif

    reg.provider_packages.append("core.ai_pack.providers")
    reg.tool_defs.update({**SCENARIO_TOOL_DEFS, **WHATIF_TOOL_DEFS, ACTION_NAME: ACTION_DEF, CHART_NAME: CHART_TOOL_DEF})
    reg.action_handlers.update({"expense": expense, "reminder": reminder, "income": income})
    reg.action_records.extend(["expense", "reminder", "income"])
    reg.param_validators.append(_validate_tool_specific_params)
    reg.business_validators.append(_business_rules)
    reg.training_families.update({"whatif": whatif, "income": income_family, "assets": assets, "banking": banking,
                                  "budget": budget, "overview": overview})
    reg.url_modules.append("core.ai_pack.urls")
    reg.data_enrichers.append(_salary_enricher)
    reg.agents["advisor_agent"] = AdvisorAgent
    reg.add_extension("advisor", _Advisor)
    reg.add_extension("category_names", _category_names)
    reg.add_extension("data_slice", _data_slice)
    reg.add_extension("write_knowledge", _write_knowledge)
