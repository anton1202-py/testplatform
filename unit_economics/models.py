from django.db import models

from core.models import Account, Platform


class ProductPrice(models.Model):
    """Модель для хранения цены товара на разных платформах """
    account = models.ForeignKey(
        Account, related_name='accounts', on_delete=models.CASCADE, verbose_name='Аккаунт')
    moy_sklad_product_number = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="ID продукта с Моего Склада")
    name = models.TextField(null=False, verbose_name="Название товара")
    brand = models.TextField(null=True, blank=True,
                             verbose_name="Бренд товара")
    vendor = models.CharField(
        max_length=255, null=False, verbose_name="Артикул товара")
    barcode = models.JSONField(
        default=list, null=False, verbose_name="Баркод товара")
    product_type = models.CharField(
        max_length=255, verbose_name='Тип товара(продукты, комплекты)')
    cost_price = models.FloatField(verbose_name='Себестоимость товара', null=True, blank=True
                                   )
    image = models.ImageField(upload_to='images/', verbose_name='Картинка продукта', null=True, blank=True
                              )

    class Meta:
        verbose_name = "Продукт с ценами для Unit экономики"
        verbose_name_plural = "Продукты с ценами для Unit экономики"


class ProductCostPrice(models.Model):
    """
    Описывает модель себестоимости Продукта
    по методу оприходования по FIFO
    """
    product = models.OneToOneField(ProductPrice, related_name='costprice_product',
                                   on_delete=models.CASCADE, verbose_name='Продукт')
    cost_price = models.FloatField(
        verbose_name='Себестоимость продукта', null=True, blank=True)

    class Meta:
        verbose_name = "Себестоимость продукта"
        verbose_name_plural = "Себестоимость продукта"


class ProductForMarketplacePrice(models.Model):
    """
    Описывает модель цен для продукта на всех маркетплейсах.
    Цены берутся из данных Моего Склада
    """
    product = models.OneToOneField(ProductPrice, related_name='price_product',
                                   on_delete=models.CASCADE, verbose_name='Продукт')
    wb_price = models.FloatField(
        verbose_name='Цена на Wildberries', null=True, blank=True)
    yandex_price = models.FloatField(
        verbose_name='Цена на Yandex', null=True, blank=True)
    rrc = models.FloatField(
        verbose_name='Рекомендованная розничная цена', null=True, blank=True)

    class Meta:
        verbose_name = "Цены для маркетплейсов"
        verbose_name_plural = "Цены для маркетплейсов"


class ProductOzonPrice(models.Model):
    """
    Описывает модель цен для ОЗОН.
    Цены берутся из данных Моего Склада
    """
    product = models.ForeignKey(ProductPrice, related_name='ozon_price_product',
                                on_delete=models.CASCADE, verbose_name='Продукт')
    account = models.ForeignKey(
        Account, related_name='ozon_price_account', on_delete=models.CASCADE, verbose_name='Аккаунт')
    ozon_price = models.FloatField(
        verbose_name='Цена на Ozon', null=True, blank=True)

    class Meta:
        verbose_name = "Цены для ОЗОН"
        verbose_name_plural = "Цены для ОЗОН"


class ProfitabilityMarketplaceProduct(models.Model):
    """Рентабельность товара на маркетплейсе"""
    mp_product = models.OneToOneField('MarketplaceProduct', related_name='mp_profitability',
                                      on_delete=models.CASCADE, verbose_name='Продукт c с маркетплейса')
    profit = models.FloatField(verbose_name='Прибыль', null=True, blank=True)
    profitability = models.FloatField(
        verbose_name='Рентабельность', null=True, blank=True)
    overheads = models.FloatField(
        verbose_name='Накладные расходы', default=0.2)

    class Meta:
        verbose_name = "Рентабельность товара на маркетплейсе"
        verbose_name_plural = "Рентабельность товара на маркетплейсе"


class PostingGoods(models.Model):
    """
    Описывает модель оприходования товара на склад
    на площадке Мой Склад. Для подсчета себестоимости
    """
    product = models.ForeignKey(ProductPrice, related_name='postinggoods_product',
                                on_delete=models.CASCADE, verbose_name='Продукт')
    receipt_date = models.DateTimeField(
        verbose_name="Дата поступления на склад")
    amount = models.IntegerField(verbose_name="Поступившее количество")
    price = models.FloatField(verbose_name='Цена поступившего товара')
    costs = models.FloatField(verbose_name='Расходы', default=0)

    class Meta:
        verbose_name = "Оприходование товара"
        verbose_name_plural = "Оприходование товара"


class MarketplaceProduct(models.Model):
    """Описывает продукт на Маркетплейсе. Ссылается на основной продукт в системе с Мой Склад"""
    account = models.ForeignKey(
        Account, related_name='mp_accounts', on_delete=models.CASCADE, verbose_name='Аккаунт')
    platform = models.ForeignKey(
        Platform, related_name='mp_plaform', on_delete=models.CASCADE, verbose_name='Платформа')
    product = models.ForeignKey(ProductPrice, related_name='mp_product',
                                on_delete=models.CASCADE, verbose_name='ПРодукт на МП')
    name = models.CharField(
        max_length=255, verbose_name="Название товара", null=True, blank=True)
    sku = models.CharField(
        max_length=255, verbose_name="Идентификатор товара на платформе")
    ozon_sku = models.CharField(
        max_length=255, verbose_name="Ozon sku для получения ссылки на товар", null=True, blank=True)
    seller_article = models.CharField(
        max_length=255, null=False, verbose_name="Артикул продавца")
    barcode = models.JSONField(
        default=list, null=False, verbose_name="Баркод товара")

    width = models.IntegerField(verbose_name='Ширина', null=True, blank=True)
    height = models.IntegerField(verbose_name='Высота', null=True, blank=True)
    length = models.IntegerField(verbose_name='Длина', null=True, blank=True)
    weight = models.FloatField(verbose_name='Вес', null=True, blank=True)
    category = models.ForeignKey('MarketplaceCategory', related_name='mp_category',
                                 on_delete=models.CASCADE, verbose_name='Категория товара', null=True, blank=True)

    class Meta:
        verbose_name = "Продукт на Маркетплейсе"
        verbose_name_plural = "Продукт на Маркетплейсе"


class MarketplaceProductPriceWithProfitability(models.Model):
    """
    Цена для продукта на маркетплейсе на основании комиссий и рентабельности
    """
    mp_product = models.OneToOneField(MarketplaceProduct, related_name='mp_product_profit_price',
                                      on_delete=models.CASCADE, verbose_name='Продукт на маркетплейсе')
    profit_price = models.FloatField(
        verbose_name='Цена на основе рентабельности и с/с по оприходованию', null=True, blank=True)
    usual_price = models.FloatField(
        verbose_name='Цена на основе рентабельности и обычной с/с', null=True, blank=True)

    class Meta:
        verbose_name = "Цена для продукта на маркетплейсе на основании рентабельности"
        verbose_name_plural = "Цена для продукта на маркетплейсе на основании рентабельности"


class MarketplaceCategory(models.Model):
    """Описывает категорию товара на Маркетплейсе."""
    platform = models.ForeignKey(
        Platform, related_name='mc_plaform', on_delete=models.CASCADE, verbose_name='Платформа')
    category_number = models.IntegerField(
        verbose_name="Номер категории", null=True, blank=True, )
    category_name = models.CharField(
        max_length=255, verbose_name="Название категории", null=True, blank=True)

    class Meta:
        verbose_name = "Категория на Маркетплейсе"
        verbose_name_plural = "Категория на Маркетплейсе"


class MarketplaceCommission(models.Model):
    """Модель для хранения процента комиссии на разных платформах"""
    marketplace_product = models.OneToOneField(MarketplaceProduct, related_name='marketproduct_comission', on_delete=models.CASCADE,
                                               verbose_name='Продукт на маркетплейсе', null=True, blank=True)
    fbs_commission = models.FloatField(
        verbose_name='Комиссия FBS', null=True, blank=True)
    fbo_commission = models.FloatField(
        verbose_name='Комиссия FBO', null=True, blank=True)
    dbs_commission = models.FloatField(
        verbose_name='Комиссия DBS', null=True, blank=True)
    fbs_express_commission = models.FloatField(
        verbose_name='Комиссия FBS Express', null=True, blank=True)

    class Meta:
        verbose_name = "Комиссия на Маркетплейсе"
        verbose_name_plural = "Комиссия на Маркетплейсе"


class MarketplaceLogistic(models.Model):
    """Модель для хранения логистических затрат на разных платформах"""
    marketplace_product = models.OneToOneField(MarketplaceProduct, related_name='marketproduct_logistic', on_delete=models.CASCADE,
                                               verbose_name='Продукт на маркетплейсе', null=True, blank=True)
    cost_logistic = models.FloatField(
        verbose_name='Логистические затраты', null=True, blank=True)
    cost_logistic_fbo = models.FloatField(
        verbose_name='Логистические затраты FBO', null=True, blank=True)
    cost_logistic_fbs = models.FloatField(
        verbose_name='Логистические затраты FBS', null=True, blank=True)

    class Meta:
        verbose_name = "Логистические затраты на Маркетплейсе"
        verbose_name_plural = "Логистические затраты на Маркетплейсе"


class MarketplaceAction(models.Model):
    """Акция на маркеплейсе"""
    platform = models.ForeignKey(
        Platform, related_name='ma_plaform', on_delete=models.CASCADE, verbose_name='Платформа')
    account = models.ForeignKey(
        Account, related_name='ma_accounts', on_delete=models.CASCADE, verbose_name='Аккаунт', null=True, blank=True)
    action_number = models.CharField(
        max_length=100, verbose_name="Идентификатор акции")
    action_name = models.CharField(
        max_length=255, verbose_name="Название акции", null=True, blank=True)
    date_start = models.DateField(
        verbose_name="Дата начала акции", null=True, blank=True)
    date_finish = models.DateField(
        verbose_name="Дата окончания акции", null=True, blank=True)

    class Meta:
        verbose_name = "Акции на Маркетплейсе"
        verbose_name_plural = "Акции на Маркетплейсе"


class MarketplaceProductInAction(models.Model):
    """Товары с маркетплейса в Акции"""
    marketplace_product = models.ForeignKey(MarketplaceProduct, related_name='product_in_action', on_delete=models.CASCADE,
                                            verbose_name='Продукт на маркетплейсе')
    action = models.ForeignKey(MarketplaceAction, related_name='action', on_delete=models.CASCADE,
                               verbose_name='Продукт на маркетплейсе')
    product_price = models.FloatField(verbose_name="Цена товара в акции")
    status = models.BooleanField(
        verbose_name="Участие товара в акции", null=True, blank=True)

    class Meta:
        verbose_name = "Товары в акции"
        verbose_name_plural = "Товары в акции"
