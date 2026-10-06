"""Version tag of the Privacy Policy / Terms of Service texts.

Label of the BUILT-IN text (static/i18n legal_* keys), used while no edited
version exists. Once a sysadmin publishes a version (Settings > Legal Text) the
newest LegalVersion label is current instead (core.services.legal.current_label).
Bump this when the built-in i18n text itself changes materially.
The current text is a DRAFT and needs legal review before public launch.
"""

LEGAL_VERSION = "2026-10-draft-1"
