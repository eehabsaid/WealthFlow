from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from wealthflow.env_settings import DEV_SECRET_KEY, build_security_settings


class EnvSecuritySettingsTests(SimpleTestCase):
    def test_defaults_keep_dev_behaviour(self):
        cfg = build_security_settings({})
        self.assertTrue(cfg["DEBUG"])
        self.assertEqual(cfg["SECRET_KEY"], DEV_SECRET_KEY)
        self.assertNotIn("SESSION_COOKIE_SECURE", cfg)
        self.assertNotIn("SECURE_SSL_REDIRECT", cfg)
        self.assertNotIn("AXES_IPWARE_PROXY_COUNT", cfg)

    def test_production_requires_secret_key(self):
        with self.assertRaises(ImproperlyConfigured):
            build_security_settings({"WEALTHFLOW_DEBUG": "false"})

    def test_production_turns_on_https_hardening(self):
        cfg = build_security_settings({"WEALTHFLOW_DEBUG": "false", "WEALTHFLOW_SECRET_KEY": "k" * 60})
        self.assertFalse(cfg["DEBUG"])
        self.assertEqual(cfg["SECRET_KEY"], "k" * 60)
        self.assertTrue(cfg["SESSION_COOKIE_SECURE"])
        self.assertTrue(cfg["CSRF_COOKIE_SECURE"])
        self.assertTrue(cfg["SECURE_SSL_REDIRECT"])
        self.assertGreater(cfg["SECURE_HSTS_SECONDS"], 0)
        self.assertNotIn("SECURE_PROXY_SSL_HEADER", cfg)  # only trusted behind a proxy

    def test_behind_proxy_sets_proxy_header_and_axes_ip(self):
        cfg = build_security_settings(
            {"WEALTHFLOW_BEHIND_PROXY": "true", "WEALTHFLOW_PROXY_COUNT": "2"}
        )
        self.assertEqual(cfg["SECURE_PROXY_SSL_HEADER"], ("HTTP_X_FORWARDED_PROTO", "https"))
        self.assertEqual(cfg["AXES_IPWARE_PROXY_COUNT"], 2)
        self.assertEqual(cfg["AXES_IPWARE_META_PRECEDENCE_ORDER"][0], "HTTP_X_FORWARDED_FOR")

    def test_hosts_and_origins_from_env(self):
        cfg = build_security_settings(
            {"WEALTHFLOW_ALLOWED_HOSTS": "a.com, b.com", "WEALTHFLOW_CSRF_TRUSTED_ORIGINS": "https://a.com"}
        )
        self.assertEqual(cfg["ALLOWED_HOSTS"], ["a.com", "b.com"])
        self.assertEqual(cfg["CSRF_TRUSTED_ORIGINS"], ["https://a.com"])
