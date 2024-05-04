import logging
import random

import pytest

from django.db import transaction
from rest_framework.test import APIClient

from core.enums import MarketplaceChoices
from core.models import Account, Platform, Product


@transaction.atomic
def get_or_create_test_platform(platform_type):
    report_type = Platform.objects.filter(platform_type=platform_type).first()

    if not report_type:
        report_type = Platform.objects.create(
            name="Test Report Type " + str(platform_type),
            platform_type=platform_type,
        )
        return report_type, True

    return report_type, False


@transaction.atomic
def get_or_create_test_account(user, platform_type):
    account = Account.objects.filter(
        user=user,
        platform=get_or_create_test_platform(platform_type)[0]
    ).first()

    if not account:
        account = Account.objects.create(
            user=user,
            platform=get_or_create_test_platform(platform_type)[0],
            name="Test Account " + str(platform_type),
        )
        return account, True

    return account, False


@transaction.atomic
def create_test_accounts(user):
    get_or_create_test_account(user, MarketplaceChoices.MOY_SKLAD)
    get_or_create_test_account(user, MarketplaceChoices.WILDBERRIES)


@transaction.atomic
def get_or_create_test_product(account, barcode=None, connection=None, has_manual_connection=False):
    random_num = str(random.randint(0, 1000000000))

    if not barcode:
        barcode = random_num

    product = Product.objects.filter(
        account=account,
        barcode=barcode,
    ).first()

    if not product:
        product = Product.objects.create(
            account=account,
            sku=f"TEST SKU {random_num}",
            has_manual_connection=has_manual_connection,
            connection=connection,
            barcode=barcode,
            name=f"Test Product {random_num}",
            vendor=f"Vendor {random_num}"
        )
        return product, True

    return product, False


@transaction.atomic
def clean_products():
    Product.objects.all().delete()


def get_test_products_1():
    return [
        {
            "sku": "Test 1",
            "barcode": "1",
            "vendor": "Test 1",
            "name": "Test 1",
        },
        {
            "sku": "Test 2",
            "barcode": "2",
            "vendor": "Test 2",
            "name": "Test 2",
        }
    ]


@pytest.mark.django_db
def test_products_deletion(
    django_user_model,
    test_user_name,
    test_user_password
):
    # Products with manual connections will not be deleted and with auto connection will be deleted
    user = django_user_model.objects.create_user(email=test_user_name, password=test_user_password)

    moy_sklad_account, created = get_or_create_test_account(user, MarketplaceChoices.MOY_SKLAD)
    moy_sklad_processor = moy_sklad_account.get_platform_processor()
    moy_sklad_processor.get_products = get_test_products_1

    get_or_create_test_product(moy_sklad_account, barcode="1")
    get_or_create_test_product(moy_sklad_account, barcode="2")
    get_or_create_test_product(moy_sklad_account, barcode="3")

    products_count_before = Product.objects.all().count()

    moy_sklad_processor.refresh_products()

    assert products_count_before != Product.objects.all().count()

    clean_products()


@pytest.mark.django_db
def test_products_deletion_with_manual_connections(
        django_user_model,
        test_user_name,
        test_user_password
):

    user = django_user_model.objects.create_user(email=test_user_name, password=test_user_password)

    moy_sklad_account, created = get_or_create_test_account(user, MarketplaceChoices.MOY_SKLAD)
    wildberries_account, created = get_or_create_test_account(user, MarketplaceChoices.WILDBERRIES)
    moy_sklad_processor = moy_sklad_account.get_platform_processor()
    moy_sklad_processor.get_products = get_test_products_1

    wildberries_processor = wildberries_account.get_platform_processor()
    wildberries_processor.get_products = get_test_products_1

    get_or_create_test_product(moy_sklad_account, barcode="1")
    get_or_create_test_product(moy_sklad_account, barcode="2")
    get_or_create_test_product(wildberries_account, barcode="1")
    get_or_create_test_product(wildberries_account, barcode="2")

    get_or_create_test_product(wildberries_account, barcode="5")

    get_or_create_test_product(wildberries_account, barcode="3", has_manual_connection=True)

    products_count_before = Product.objects.all().count()

    moy_sklad_processor.refresh_products()
    wildberries_processor.refresh_products()

    assert products_count_before - 1 == Product.objects.all().count()

    clean_products()


@pytest.mark.django_db
def test_products_update(
        django_user_model,
        test_user_name,
        test_user_password
):
    user = django_user_model.objects.create_user(email=test_user_name, password=test_user_password)

    moy_sklad_account, created = get_or_create_test_account(user, MarketplaceChoices.MOY_SKLAD)
    moy_sklad_processor = moy_sklad_account.get_platform_processor()
    moy_sklad_processor.get_products = get_test_products_1

    product, created = get_or_create_test_product(moy_sklad_account, barcode="1")

    old_product_name = product.name

    moy_sklad_processor.refresh_products()

    product_changed, created = get_or_create_test_product(moy_sklad_account, barcode="1")

    assert product.id == product_changed.id
    assert old_product_name != product_changed.name

    clean_products()


@pytest.mark.django_db
def test_products_update_with_connections(
        django_user_model,
        test_user_name,
        test_user_password
):
    user = django_user_model.objects.create_user(email=test_user_name, password=test_user_password)

    moy_sklad_account, created = get_or_create_test_account(user, MarketplaceChoices.MOY_SKLAD)
    wildberries_account, created = get_or_create_test_account(user, MarketplaceChoices.WILDBERRIES)
    moy_sklad_processor = moy_sklad_account.get_platform_processor()
    moy_sklad_processor.get_products = get_test_products_1

    wildberries_processor = wildberries_account.get_platform_processor()
    wildberries_processor.get_products = get_test_products_1

    product_moy_sklad, created = get_or_create_test_product(moy_sklad_account, barcode="1")
    product_wildberries, created = get_or_create_test_product(
        wildberries_account,
        barcode="1",
        connection=product_moy_sklad
    )

    old_product_connection = product_wildberries.connection.id

    moy_sklad_processor.refresh_products()

    product_changed, created = get_or_create_test_product(wildberries_account, barcode="1")

    assert product_wildberries.id == product_changed.id
    assert old_product_connection == product_changed.connection.id


@pytest.mark.django_db
def test_connections_creation(
        django_user_model,
        test_user_name,
        test_user_password
):
    #
    user = django_user_model.objects.create_user(email=test_user_name, password=test_user_password)

    moy_sklad_account, created = get_or_create_test_account(user, MarketplaceChoices.MOY_SKLAD)
    wildberries_account, created = get_or_create_test_account(user, MarketplaceChoices.WILDBERRIES)
    moy_sklad_processor = moy_sklad_account.get_platform_processor()
    moy_sklad_processor.get_products = get_test_products_1

    wildberries_processor = wildberries_account.get_platform_processor()
    wildberries_processor.get_products = get_test_products_1

    product_moy_sklad_1, created = get_or_create_test_product(moy_sklad_account, barcode="1")
    product_wildberries_1, created = get_or_create_test_product(
        wildberries_account,
        barcode="1",
    )
    product_wildberries_2, created = get_or_create_test_product(
        wildberries_account,
        barcode="2",
        connection=product_moy_sklad_1,
        has_manual_connection=True
    )

    old_product_wildberries_2_connection = product_wildberries_2.connection.id

    moy_sklad_processor.refresh_products()

    user.refresh_user_products_connections()

    product_changed_dynamic, created = get_or_create_test_product(
        wildberries_account,
        barcode="1"
    )

    product_changed_manual, created = get_or_create_test_product(
        wildberries_account,
        barcode="2"
    )

    assert product_changed_dynamic.connection is not None
    assert old_product_wildberries_2_connection == product_changed_manual.connection.id
