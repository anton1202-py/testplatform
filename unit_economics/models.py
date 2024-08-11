from django.db import models

from core.models import Product, Platform


class ProductPrice(models.Model):
    """Модель для хранения цены товара на разных платформах"""
    product = models.ForeignKey(Product, related_name='prices', on_delete=models.CASCADE, verbose_name='Товар')
    platform = models.ForeignKey(Platform, related_name='platforms', on_delete=models.CASCADE, verbose_name='Платформа')
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Цена товара')
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                     verbose_name='Себестоимость товара')


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
