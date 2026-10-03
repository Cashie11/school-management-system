"""Tests for the environment parsing helpers in the settings module.

Deployments commonly paste a full ``https://host/`` URL into the host settings.
These helpers normalise that instead of letting every request fail with a
``DisallowedHost`` error.
"""

import os

from django.test import SimpleTestCase

from config.settings import env_hosts, env_origins


class EnvHostsTests(SimpleTestCase):
    def tearDown(self):
        os.environ.pop("TEST_HOSTS", None)

    def parse(self, value):
        os.environ["TEST_HOSTS"] = value
        return env_hosts("TEST_HOSTS")

    def test_plain_hosts(self):
        self.assertEqual(
            self.parse("example.com, www.example.com"),
            ["example.com", "www.example.com"],
        )

    def test_full_url_is_normalised(self):
        self.assertEqual(self.parse("https://school.example.com/"), ["school.example.com"])

    def test_scheme_port_and_path_are_removed(self):
        self.assertEqual(self.parse("http://example.com:8000/admin"), ["example.com"])

    def test_credentials_are_removed(self):
        self.assertEqual(self.parse("https://user:pass@example.com"), ["example.com"])

    def test_duplicates_are_removed(self):
        self.assertEqual(self.parse("example.com,https://example.com"), ["example.com"])

    def test_case_is_normalised(self):
        self.assertEqual(self.parse("School.Example.COM"), ["school.example.com"])

    def test_bracketed_ipv6_is_kept_intact(self):
        self.assertEqual(self.parse("[::1]"), ["[::1]"])

    def test_wildcard_is_kept(self):
        self.assertEqual(self.parse("*"), ["*"])

    def test_hosts_survive_only_scheme(self):
        self.assertEqual(self.parse("https://"), [])


class EnvOriginsTests(SimpleTestCase):
    def tearDown(self):
        os.environ.pop("TEST_ORIGINS", None)

    def parse(self, value):
        os.environ["TEST_ORIGINS"] = value
        return env_origins("TEST_ORIGINS")

    def test_scheme_is_added_when_missing(self):
        self.assertEqual(self.parse("school.example.com"), ["https://school.example.com"])

    def test_trailing_slash_is_removed(self):
        self.assertEqual(self.parse("https://school.example.com/"), ["https://school.example.com"])

    def test_path_is_dropped(self):
        self.assertEqual(self.parse("https://school.example.com/admin"), ["https://school.example.com"])

    def test_port_is_kept(self):
        self.assertEqual(self.parse("http://localhost:8000"), ["http://localhost:8000"])

    def test_duplicates_are_removed(self):
        self.assertEqual(
            self.parse("https://a.example.com,https://a.example.com/"),
            ["https://a.example.com"],
        )
