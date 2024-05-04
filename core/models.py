from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models

from core.enums import MarketplaceChoices
from core.integrations import (
    MyWarehouseIntegration,
    OZONIntegration,
    SberMarketIntegration,
    WildBerriesIntegration,
    YandexIntegration,
)
from core.manager import CustomUserManager
from stock.integrations import (
    MyWarehouseOrdersIntegration,
    OzonOrdersIntegration,
    WildBerriesOrdersIntegration,
    YandexOrdersIntegration,
)


class User(AbstractBaseUser, PermissionsMixin):
    """Пользователь системы"""

    email = models.EmailField(
        unique=True,
        verbose_name="Адрес электронной почты",
        max_length=255,
        blank=False,
        null=False,
    )

    created_on = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания пользователя")
    updated_on = models.DateTimeField(
        auto_now=True,
        verbose_name="Последняя дата обновления информации о пользователе",
    )

    is_active = models.BooleanField(default=True, verbose_name="Флаг активного (не заблокированного) аккаунта")
    is_staff = models.BooleanField(default=False, verbose_name="Является ли админом")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = "Пользователь аналитической платформы"
        verbose_name_plural = "Пользователи аналитической платформы"

    def refresh_user_products_connections(self):
        moy_sklad_products = Product.objects.filter(
            account__in=self.accounts.all(),
            account__platform__platform_type=MarketplaceChoices.MOY_SKLAD,
        )
        other_products = Product.objects.filter(account__in=self.accounts.all(), has_manual_connection=False).exclude(
            account__platform__platform_type=MarketplaceChoices.MOY_SKLAD
        )

        bulk_update_list = []

        for item in other_products:
            filtered_data = list(filter(lambda product: product.barcode == item.barcode, moy_sklad_products))
            if len(filtered_data) != 0:
                item.connection = filtered_data[0]
            else:
                item.connection = None
            item.has_manual_connection = False
            bulk_update_list.append(item)

        Product.objects.bulk_update(bulk_update_list, fields=["connection", "has_manual_connection"])


def default_authorization_fields():
    return {}


class Platform(models.Model):
    """Платформа, на которой находятся товары"""

    name = models.CharField(max_length=100, null=False, verbose_name="Название")

    platform_type = models.IntegerField(
        choices=MarketplaceChoices.choices,
        default=MarketplaceChoices.WILDBERRIES,
        null=False,
        blank=False,
        verbose_name="Платформа",
    )

    def get_integration_processor_class(self):
        if self.platform_type == MarketplaceChoices.WILDBERRIES:
            processor_class = WildBerriesIntegration
        elif self.platform_type == MarketplaceChoices.YANDEX_MARKET:
            processor_class = YandexIntegration
        elif self.platform_type == MarketplaceChoices.MEGA_MARKET:
            processor_class = SberMarketIntegration
        elif self.platform_type == MarketplaceChoices.OZON:
            processor_class = OZONIntegration
        elif self.platform_type == MarketplaceChoices.MOY_SKLAD:
            processor_class = MyWarehouseIntegration
        else:
            raise NotImplementedError
        return processor_class

    def get_integration_orders_processor_class(self):
        if self.platform_type == MarketplaceChoices.WILDBERRIES:
            processor_class = WildBerriesOrdersIntegration
        elif self.platform_type == MarketplaceChoices.YANDEX_MARKET:
            processor_class = YandexOrdersIntegration
        elif self.platform_type == MarketplaceChoices.MEGA_MARKET:
            raise NotImplementedError
        elif self.platform_type == MarketplaceChoices.OZON:
            processor_class = OzonOrdersIntegration
        elif self.platform_type == MarketplaceChoices.MOY_SKLAD:
            processor_class = MyWarehouseOrdersIntegration
        else:
            raise NotImplementedError

        return processor_class

    @property
    def auth_fields_description(self):
        return self.get_integration_processor_class().auth_fields_description

    def __str__(self):
        return self.name


class Account(models.Model):
    """Аккаунт пользователя на платформе"""

    AUTH_TYPE_CHOICES = (
        ("BASIC", "basic"),
        ("TOKEN", "token"),
    )

    user = models.ForeignKey(
        User,
        related_name="accounts",
        null=False,
        on_delete=models.CASCADE,
        verbose_name="Пользователь, которому принадлежит аккаунт",
    )

    platform = models.ForeignKey(
        Platform,
        related_name="accounts",
        null=False,
        on_delete=models.CASCADE,
        verbose_name="Платформа, для которой заведен аккаунт",
    )

    name = models.CharField(max_length=100, null=False, verbose_name="Название")

    authorization_fields = models.JSONField(
        null=False, blank=False, default=default_authorization_fields, verbose_name="Описание полей в виде json"
    )

    def get_platform_processor(self):
        return self.platform.get_integration_processor_class()(self)

    def get_platform_orders_processor(self):
        return self.platform.get_integration_orders_processor_class()(self)

    def __str__(self):
        return f"{self.platform}: {self.name}"

    class Meta:
        verbose_name = "Аккаунт пользователя на платформе"
        verbose_name_plural = "Аккаунты пользователей на платформе"


class Product(models.Model):
    """Товар на платформе"""

    account = models.ForeignKey(
        Account,
        related_name="products",
        null=False,
        on_delete=models.CASCADE,
        verbose_name="Аккаунт к которому относятся продукты",
    )

    name = models.TextField(null=False, verbose_name="Название")
    brand = models.TextField(null=True, blank=True, verbose_name="Бренд")
    sku = models.CharField(max_length=255, verbose_name="Идентификатор товара на платформе")
    vendor = models.CharField(max_length=255, null=False, verbose_name="Артикул")
    barcode = models.CharField(max_length=255, null=False, verbose_name="Баркод")

    connection = models.ForeignKey(
        "self",
        related_name="connections",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    has_manual_connection = models.BooleanField(
        default=False, null=False, blank=False, verbose_name="Связь создана в ручную"
    )

    def __str__(self):
        return f"{self.sku}: {self.name}"

    class Meta:
        verbose_name = "Товар на платформе"
        verbose_name_plural = "Товары на платформе"
