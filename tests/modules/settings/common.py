"""Shared helper for tests/modules/settings/ phase files."""

import time


def _uid():
    return str(int(time.time() * 1000))[-6:]
