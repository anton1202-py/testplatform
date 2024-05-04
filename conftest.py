import pytest
from django.db import transaction

from core.models import User


def create_test_user(name):
    user = User.objects.create_user(email=name, password="test123")
    user.is_active = True
    user.save()
    return user


@transaction.atomic
def get_or_create_test_user():
    user = User.objects.filter(email="test_user@test.com").first()

    if not user:
        user = create_test_user("test_user@test.com")
        return user, True

    return user, False


@pytest.fixture()
def test_user_name():
    """Возвращает тестового пользователя"""
    return "test@test.test"


@pytest.fixture()
def test_user_password():
    """Возвращает тестового пользователя"""
    return "testtest"
