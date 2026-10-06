"""Re-consent: who must accept the current legal version, and recording it."""

from django.utils import timezone

from core.services.legal import content


def needs_reconsent(profile) -> bool:
    """True when the newest version demands re-consent and this account has not accepted it.

    Accounts keep the terms_version they accepted; only a version published with
    `require_reconsent` asks them again, and only until they accept it.
    """
    if profile is None or not content.current_requires_reconsent():
        return False
    return (profile.terms_version or "").strip() != content.current_label()


def accept_current(profile) -> str:
    label = content.current_label()
    profile.terms_version = label
    profile.terms_accepted_at = timezone.now()
    profile.save(update_fields=["terms_version", "terms_accepted_at"])
    return label
