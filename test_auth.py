import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User


@pytest.mark.django_db
class TestEmailCaseInsensitivity:
    def test_duplicate_email_in_other_case_rejected(self):
        c = APIClient()
        assert c.post(reverse('auth-register'), {'email': 'Dup@Example.invalid', 'password': 'StrongPass123!', 'date_of_birth': '1990-01-15'},
                      format='json').status_code == 201
        assert c.post(reverse('auth-register'), {'email': 'dup@example.INVALID', 'password': 'StrongPass123!', 'date_of_birth': '1990-01-15'},
                      format='json').status_code == 400

    def test_login_is_case_insensitive(self):
        User.objects.create_user(email='Login@Example.invalid', password='StrongPass123!')
        r = APIClient().post(reverse('auth-login'),
                             {'email': 'LOGIN@example.invalid', 'password': 'StrongPass123!'}, format='json')
        assert r.status_code == 200 and 'access' in r.data

    def test_weak_password_rejected_with_error_shape(self):
        r = APIClient().post(reverse('auth-register'),
                             {'email': 'w@example.invalid', 'password': 'password', 'date_of_birth': '1990-01-15'}, format='json')
        assert r.status_code == 400 and 'error' in r.data and 'fields' in r.data['error']


@pytest.mark.django_db
class TestLogout:
    def test_cannot_blacklist_someone_elses_refresh_token(self):
        a = User.objects.create_user(email='a@example.invalid', password='StrongPass123!')
        b = User.objects.create_user(email='b@example.invalid', password='StrongPass123!')
        c = APIClient()
        c.force_authenticate(user=a)
        r = c.post(reverse('auth-logout'), {'refresh': str(RefreshToken.for_user(b))}, format='json')
        assert r.status_code == 400

    def test_logout_blacklists_own_token(self):
        a = User.objects.create_user(email='a2@example.invalid', password='StrongPass123!')
        refresh = str(RefreshToken.for_user(a))
        c = APIClient()
        c.force_authenticate(user=a)
        assert c.post(reverse('auth-logout'), {'refresh': refresh}, format='json').status_code == 205
        assert APIClient().post(reverse('auth-refresh'), {'refresh': refresh}, format='json').status_code == 401


@pytest.mark.django_db
def test_login_is_throttled():
    c = APIClient()
    codes = [c.post(reverse('auth-login'), {'email': 'x@example.invalid', 'password': 'nope'},
                    format='json').status_code for _ in range(25)]
    assert 429 in codes
