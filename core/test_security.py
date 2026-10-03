from django.conf import settings
from django.test import TestCase


class SecuritySettingsTests(TestCase):
    """Always-on hardening.

    The stricter options (HTTPS redirect, secure cookies, HSTS) derive from
    DJANGO_DEBUG and are verified with `manage.py check --deploy`.
    """

    def test_cookie_and_header_hardening_is_on(self):
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, "Lax")
        self.assertEqual(settings.CSRF_COOKIE_SAMESITE, "Lax")
        self.assertEqual(settings.X_FRAME_OPTIONS, "DENY")
        self.assertTrue(settings.SECURE_CONTENT_TYPE_NOSNIFF)
        self.assertEqual(settings.SECURE_REFERRER_POLICY, "same-origin")
        self.assertEqual(settings.SECURE_PROXY_SSL_HEADER, ("HTTP_X_FORWARDED_PROTO", "https"))

    def test_the_https_options_move_together(self):
        # They all come from the same DEBUG-derived default, so they should never
        # disagree with each other.
        self.assertEqual(settings.SESSION_COOKIE_SECURE, settings.CSRF_COOKIE_SECURE)
        self.assertEqual(settings.SECURE_SSL_REDIRECT, settings.SESSION_COOKIE_SECURE)

    def test_a_secret_key_is_always_present(self):
        self.assertTrue(settings.SECRET_KEY)
