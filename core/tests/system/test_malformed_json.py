import json
import re

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import URLPattern, URLResolver, get_resolver

from core.middleware import JsonBodyErrorMiddleware
from core.validators.json_body import BadJsonError, parse_json_body

User = get_user_model()


def _iter_paths(patterns, prefix=""):
    """Yield every concrete URL path (route params filled with a dummy value)."""
    for pattern in patterns:
        route = getattr(pattern.pattern, "_route", None)
        if route is None:
            continue
        route = re.sub(r"<(?:\w+:)?\w+>", "1", route)
        if isinstance(pattern, URLResolver):
            yield from _iter_paths(pattern.url_patterns, prefix + route)
        elif isinstance(pattern, URLPattern):
            yield "/" + prefix + route


class ParseJsonBodyTests(TestCase):
    def _req(self, body):
        return RequestFactory().post("/x/", data=body, content_type="application/json")

    def test_valid_and_empty_bodies(self):
        self.assertEqual(parse_json_body(self._req(json.dumps({"a": 1}))), {"a": 1})
        self.assertEqual(parse_json_body(self._req("")), {})

    def test_bad_bodies_raise(self):
        for body in ("{bad", "[1]", '"s"', "null", "5"):
            with self.assertRaises(BadJsonError):
                parse_json_body(self._req(body))
        self.assertEqual(parse_json_body(self._req("[1]"), allow_list=True), [1])

    def test_middleware_maps_to_400(self):
        response = JsonBodyErrorMiddleware(lambda r: None).process_exception(self._req("{"), BadJsonError())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), {"error": "Invalid JSON body"})


class MalformedJsonSweepTests(TestCase):
    """No POST endpoint may answer 500 to a malformed JSON body."""

    def _sweep(self, user):
        self.client.raise_request_exception = False
        self.client.force_login(user)
        paths = sorted(set(_iter_paths(get_resolver().url_patterns)))
        self.assertGreater(len(paths), 200)
        failures = []
        for path in paths:
            if path.startswith(("/admin", "/static", "/media")):
                continue
            response = self.client.post(path, data="{bad json", content_type="application/json")
            if response.status_code >= 500:
                failures.append((path, response.status_code))
        return failures

    def test_no_endpoint_returns_500_for_superuser(self):
        admin = User.objects.create_superuser(username="sweep_admin", password="pw12345", email="a@example.com")
        self.assertEqual(self._sweep(admin), [])

    def test_no_endpoint_returns_500_for_regular_user(self):
        user = User.objects.create_user(username="sweep_user", password="pw12345")
        self.assertEqual(self._sweep(user), [])
