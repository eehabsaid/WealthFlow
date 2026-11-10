"""WealthFlow's answers to the AI app's host hooks (wired in wealthflow/settings.py, see ai/host.py)."""


def sysadmin_check(user):
    from core.authentication.utils.auth_utils import user_is_sysadmin
    return user_is_sysadmin(user)


def permission_check(user, key):
    from core.authentication.utils.auth_utils import effective_permission_keys
    return key in effective_permission_keys(user)


def audit_hook(user, event_type, actor=None, details=""):
    from core.authentication.utils.auth_utils import record_audit
    record_audit(user, event_type, actor=actor, details=details)


def feature_gate(flag):
    from core.services.billing import feature_required
    return feature_required(flag)


def base_currency(user):
    from core.services.shared.base_currency import get_user_base_code
    return get_user_base_code(user)


def default_currency():
    from core.services.shared.base_currency import platform_default_code
    return platform_default_code()


def exchange_rate(from_code, to_code):
    from core.services.shared.currency_conversion_service import CurrencyConversionService
    return CurrencyConversionService.calculate_exchange_rate(from_code, to_code)
