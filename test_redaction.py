import logging
import unittest

from securitylog.redaction import RedactingFilter, redact

JWT = 'eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiYWJjIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'


class Redact(unittest.TestCase):
    def test_jwt_and_bearer(self):
        out = redact(f'token {JWT} and Authorization: Bearer abc.def-123')
        self.assertNotIn('eyJhbGci', out)
        self.assertNotIn('abc.def-123', out)

    def test_password_forms(self):
        for s in ['password=hunter2', '{"password": "hunter2"}', "password: 'hunter2'", 'new_password=hunter2&x=1', 'PASSWD=hunter2']:
            self.assertNotIn('hunter2', redact(s), s)

    def test_refresh_and_access_tokens(self):
        out = redact('{"refresh": "r-token-123456", "access": "a-token-654321"}')
        self.assertNotIn('r-token-123456', out)
        self.assertNotIn('a-token-654321', out)

    def test_email_addresses(self):
        self.assertEqual(redact('login failed for alice@example.org'), 'login failed for [email]')

    def test_harmless_text_is_untouched(self):
        s = 'security event recorded: login_failed ip=203.0.113.0/24'
        self.assertEqual(redact(s), s)


class FilterOnRealLogger(unittest.TestCase):
    def _capture(self, emit):
        logger = logging.getLogger('veya.test.redaction')
        logger.handlers.clear()
        logger.propagate = False
        records = []

        class H(logging.Handler):
            def emit(self_inner, record):
                records.append(self_inner.format(record))
        h = H()
        h.addFilter(RedactingFilter())
        logger.addHandler(h)
        logger.setLevel(logging.INFO)
        emit(logger)
        return records

    def test_message_args_are_redacted(self):
        out = self._capture(lambda lg: lg.info('payload %s', {'password': 'hunter2', 'email': 'a@b.co'}))
        self.assertNotIn('hunter2', out[0])
        self.assertNotIn('a@b.co', out[0])

    def test_traceback_text_is_redacted(self):
        def boom(lg):
            try:
                raise ValueError('bad login password=hunter2 for bob@example.org')
            except ValueError:
                lg.exception('failed')
        out = self._capture(boom)[0]
        self.assertNotIn('hunter2', out)
        self.assertNotIn('bob@example.org', out)
        self.assertIn('ValueError', out)


if __name__ == '__main__':
    unittest.main()
