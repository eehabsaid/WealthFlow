"""Host layout settings ai/ reads (all optional; see ai/INSTALL.md).

  AI_HOST_APPS    ["myapp"]    Django app labels of the host whose models/code the AI may describe (default: none)
  AI_CODE_ROOTS   ["myapp","ai"]  folders the coding tools index and the agent may read (default: ["ai"])
"""
from django.conf import settings


def host_apps() -> list[str]:
    return list(getattr(settings, "AI_HOST_APPS", []))


def code_index_roots() -> list[str]:
    return list(getattr(settings, "AI_CODE_ROOTS", ["ai"]))


def code_scan_roots() -> list[str]:
    """Top-level package folders scanned for the code map: the host apps, then ai."""
    return host_apps() + ["ai"]


def host_module_prefixes() -> tuple[str, ...]:
    return tuple(f"{a}." for a in host_apps())
