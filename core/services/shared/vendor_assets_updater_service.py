"""Vendor assets updater — refreshes the locally vendored copies of
third-party frontend libraries (Bootstrap, Bootstrap Icons, Chart.js,
Leaflet) that WealthFlow serves locally so the app works fully offline
by default.

WealthFlow always runs against these local vendored copies; this
service is only used when an admin manually asks to check for updates
from Settings > Backup & Restore, while internet access happens to be
available. It first checks each library's latest published version via
a tiny npm registry lookup, and only downloads the (larger) asset files
for libraries that actually changed — nothing is downloaded if
everything is already current. On any download/swap failure, the
existing working assets for that library are left untouched.
"""

import json
import os
import shutil
import tempfile
import urllib.request
from datetime import datetime

from django.conf import settings

VENDOR_DIR = os.path.join(settings.BASE_DIR, "static", "vendor")
MANIFEST_PATH = os.path.join(VENDOR_DIR, "manifest.json")

_TIMEOUT = 15
_USER_AGENT = "Mozilla/5.0 (compatible; WealthFlow-VendorAssetsUpdater)"

# npm package name -> [(relative dest path under vendor/, cdn url template with {v})]
_LIBRARIES = {
    "bootstrap": [
        ("bootstrap/css/bootstrap.min.css", "https://cdn.jsdelivr.net/npm/bootstrap@{v}/dist/css/bootstrap.min.css"),
        ("bootstrap/js/bootstrap.bundle.min.js", "https://cdn.jsdelivr.net/npm/bootstrap@{v}/dist/js/bootstrap.bundle.min.js"),
    ],
    "bootstrap-icons": [
        ("bootstrap-icons/bootstrap-icons.css", "https://cdn.jsdelivr.net/npm/bootstrap-icons@{v}/font/bootstrap-icons.css"),
        ("bootstrap-icons/fonts/bootstrap-icons.woff2", "https://cdn.jsdelivr.net/npm/bootstrap-icons@{v}/font/fonts/bootstrap-icons.woff2"),
        ("bootstrap-icons/fonts/bootstrap-icons.woff", "https://cdn.jsdelivr.net/npm/bootstrap-icons@{v}/font/fonts/bootstrap-icons.woff"),
    ],
    "chart.js": [
        ("chartjs/chart.umd.js", "https://cdn.jsdelivr.net/npm/chart.js@{v}/dist/chart.umd.min.js"),
    ],
    "leaflet": [
        ("leaflet/leaflet.css", "https://cdn.jsdelivr.net/npm/leaflet@{v}/dist/leaflet.css"),
        ("leaflet/leaflet.js", "https://cdn.jsdelivr.net/npm/leaflet@{v}/dist/leaflet.js"),
        ("leaflet/images/layers.png", "https://cdn.jsdelivr.net/npm/leaflet@{v}/dist/images/layers.png"),
        ("leaflet/images/layers-2x.png", "https://cdn.jsdelivr.net/npm/leaflet@{v}/dist/images/layers-2x.png"),
        ("leaflet/images/marker-icon.png", "https://cdn.jsdelivr.net/npm/leaflet@{v}/dist/images/marker-icon.png"),
        ("leaflet/images/marker-icon-2x.png", "https://cdn.jsdelivr.net/npm/leaflet@{v}/dist/images/marker-icon-2x.png"),
        ("leaflet/images/marker-shadow.png", "https://cdn.jsdelivr.net/npm/leaflet@{v}/dist/images/marker-shadow.png"),
    ],
}


def _read_manifest():
    if not os.path.isfile(MANIFEST_PATH):
        return {}
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        return json.load(f)


def _write_manifest(manifest):
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def _fetch_latest_version(pkg_name):
    """Tiny npm registry lookup — just a version string, not the assets."""
    req = urllib.request.Request(
        f"https://registry.npmjs.org/{pkg_name}/latest",
        headers={"User-Agent": _USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["version"]


def _download(url, dest_path):
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        data = resp.read()
    if not data:
        raise ValueError(f"Empty response from {url}")
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, "wb") as f:
        f.write(data)


def check_for_updates():
    """Checks the latest published version of each vendored library
    against the manifest, without downloading any asset files.
    Returns {pkg_name: {"current": str, "latest": str}} for libraries
    that have a newer version available."""
    manifest = _read_manifest()
    outdated = {}
    for pkg_name in _LIBRARIES:
        current = manifest.get(pkg_name)
        latest = _fetch_latest_version(pkg_name)
        if current != latest:
            outdated[pkg_name] = {"current": current, "latest": latest}
    return outdated


def _update_library(pkg_name, version, temp_root):
    for rel_path, url_template in _LIBRARIES[pkg_name]:
        _download(url_template.format(v=version), os.path.join(temp_root, rel_path))


def _swap_in(rel_path, temp_root):
    src = os.path.join(temp_root, rel_path)
    dest = os.path.join(VENDOR_DIR, rel_path)
    backup = None
    if os.path.isfile(dest):
        backup = f"{dest}.bak_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        shutil.move(dest, backup)
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.move(src, dest)
    except Exception:
        if backup and os.path.isfile(backup):
            shutil.move(backup, dest)
        raise
    if backup and os.path.isfile(backup):
        os.remove(backup)


def update_vendor_assets():
    """Checks for newer versions first. If everything is already
    current, returns without downloading anything. Otherwise downloads
    only the libraries that changed and swaps them in one at a time,
    keeping any library that fails to download/swap on its existing
    working copy. Returns (updated: bool, success: bool, message: str)."""
    try:
        outdated = check_for_updates()
    except Exception as exc:
        return False, False, f"Could not check for updates: {exc}"

    if not outdated:
        return False, True, "Already up to date. Nothing was downloaded."

    manifest = _read_manifest()
    updated_libs, failed_libs = [], []
    temp_root = tempfile.mkdtemp(prefix="wf_vendor_update_")
    try:
        for pkg_name, versions in outdated.items():
            latest = versions["latest"]
            try:
                _update_library(pkg_name, latest, temp_root)
                for rel_path, _ in _LIBRARIES[pkg_name]:
                    _swap_in(rel_path, temp_root)
                manifest[pkg_name] = latest
                updated_libs.append(pkg_name)
            except Exception:
                failed_libs.append(pkg_name)
        _write_manifest(manifest)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    if updated_libs and not failed_libs:
        return True, True, f"Updated: {', '.join(updated_libs)}."
    if updated_libs and failed_libs:
        return True, True, (
            f"Updated: {', '.join(updated_libs)}. "
            f"Kept existing working copies for: {', '.join(failed_libs)}."
        )
    return False, False, f"Update failed, existing assets kept for: {', '.join(failed_libs)}."
