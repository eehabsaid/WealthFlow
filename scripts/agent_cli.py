"""Shared start-up for the coding-agent scripts: Django-free, run from anywhere inside the project."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wealthflow.settings")

import django  # noqa: E402

django.setup()
