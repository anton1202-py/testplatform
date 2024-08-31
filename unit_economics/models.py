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
    product_type = models.CharField(max_length=255, verbose_name='Тип товара(продукты, комплекты)')
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Цена товара')
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                     verbose_name='Себестоимость товара')

    class Meta:
        verbose_name = "Продукт с ценами для Unit экономики"
        verbose_name_plural = "Продукты с ценами для Unit экономики"


class MarketplaceProduct(models.Model):
    """Описывает продукт на Маркетплейсе. Ссылается на основной продукт в системе с Мой Склад"""
    account = models.ForeignKey(Account, related_name='mp_accounts', on_delete=models.CASCADE, verbose_name='Аккаунт')
    platform = models.ForeignKey(Platform, related_name='mp_plaform', on_delete=models.CASCADE, verbose_name='Платформа')
    product = models.ForeignKey(ProductPrice, related_name='mp_product', on_delete=models.CASCADE, verbose_name='ПРодукт на WB')
    name = models.TextField(null=False, verbose_name="Название товара")
    brand = models.TextField(null=True, blank=True, verbose_name="Бренд товара")
    sku = models.CharField(max_length=255, verbose_name="Идентификатор товара на платформе")
    vendor = models.CharField(max_length=255, null=False, verbose_name="Артикул продавца")
    barcode = models.JSONField(default=list, null=False, verbose_name="Баркод товара")
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Цена товара')

    width =  models.IntegerField(verbose_name='Ширина', null=True, blank=True)
    height = models.IntegerField(verbose_name='Высота', null=True, blank=True)
    length = models.IntegerField(verbose_name='Длина', null=True, blank=True)
    weight = models.DecimalField(verbose_name='Вес', max_digits=10, decimal_places=2, null=True, blank=True)
    category_number = models.IntegerField(null=True, blank=True, verbose_name="Номер категории")
    category_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Название категории")

    class Meta:
        verbose_name = "Продукт на Маркетплейсе"
        verbose_name_plural = "Продукт на Маркетплейсе"


class MarketplaceCommission(models.Model):
    """Модель для хранения процента комиссии на разных платформах"""
    marketplace_product = models.ForeignKey(MarketplaceProduct, related_name='marketproduct_comission', on_delete=models.CASCADE,
                                 verbose_name='Продукт на маркетплейсе', null=True, blank=True)
    fbs_commission = models.DecimalField(max_digits=10, decimal_places=2, 
        verbose_name='Комиссия FBS', null=True, blank=True)
    fbo_commission = models.DecimalField(max_digits=10, decimal_places=2,
        verbose_name='Комиссия FBO', null=True, blank=True)
    dbs_commission = models.DecimalField(max_digits=10, decimal_places=2,
        verbose_name='Комиссия DBS',null=True, blank=True)
    fbs_express_commission = models.DecimalField(max_digits=10, decimal_places=2,
        verbose_name='Комиссия FBS Express', null=True, blank=True)
    
    class Meta:
        verbose_name = "Комиссия на Маркетплейсе"
        verbose_name_plural = "Комиссия на Маркетплейсе"


class MarketplaceLogistic(models.Model):
    """Модель для хранения логистических затрат на разных платформах"""
    marketplace_product = models.ForeignKey(MarketplaceProduct, related_name='marketproduct_logistic', on_delete=models.CASCADE,
                                 verbose_name='Продукт на маркетплейсе', null=True, blank=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Логистические затраты', null=True, blank=True)
    cost_logistic_fbo = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Логистические затраты FBO', null=True, blank=True)
    cost_logistic_fbs = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Логистические затраты FBS', null=True, blank=True)

    class Meta:
        verbose_name = "Логистические затраты на Маркетплейсе"
        verbose_name_plural = "Логистические затраты на Маркетплейсе"
