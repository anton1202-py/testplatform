from django.db import models

from core.models import Product, Platform, Account


class ProductPrice(models.Model):
    """Модель для хранения цены товара на разных платформах"""
    account = models.ForeignKey(Account, related_name='accounts', on_delete=models.CASCADE, verbose_name='Аккаунт')
    platform = models.ForeignKey(Platform, related_name='prices', on_delete=models.CASCADE, verbose_name='Платформа')
    name = models.TextField(null=False, verbose_name="Название товара")
    brand = models.TextField(null=True, blank=True, verbose_name="Бренд товара")
    sku = models.CharField(max_length=255, verbose_name="Идентификатор товара на платформе")
    vendor = models.CharField(max_length=255, null=False, verbose_name="Артикул товара")
    barcode = models.JSONField(default=list, null=False, verbose_name="Баркод товара")
    type = models.CharField(max_length=255, verbose_name='Тип товара(продукты, комплекты)')
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Цена товара')
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                     verbose_name='Себестоимость товара')

    class Meta:
        verbose_name = "Продукт с ценами для Unit экономики"
        verbose_name_plural = "Продукты с ценами для Unit экономики"

class MarketplaceCommission(models.Model):
    """Модель для хранения процента комиссии на разных платформах"""
    platform = models.ForeignKey(Platform, related_name='commissions', on_delete=models.CASCADE,
                                 verbose_name='Платформа')
    category = models.CharField(max_length=255, verbose_name='Категория товара')
    dimensions = models.CharField(max_length=255, verbose_name='Габариты товара')
    commission = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Комиссия')


class MarketplaceLogistic(models.Model):
    """Модель для хранения логистических затрат на разных платформах"""
    platform = models.ForeignKey(Platform, related_name='logistics', on_delete=models.CASCADE, verbose_name='Платформа')
    region = models.CharField(max_length=255, verbose_name='Регион')
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Логистические затраты')
