"""Shared fixtures for the soft-delete tests."""


import json

from django.contrib.auth import get_user_model



User = get_user_model()
PW = "Pass12345!"


def _post(client, url, body):
    return client.post(url, json.dumps(body), content_type="application/json")
