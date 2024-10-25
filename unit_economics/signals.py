from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from unit_economics.integrations import (changer_price_with_profitability,
                                         changer_profitability_calculate)
from unit_economics.models import (MarketplaceCommission, MarketplaceLogistic,
                                   MarketplaceProduct,
                                   MarketplaceProductPriceWithProfitability,
                                   ProductCostPrice,
                                   ProductForMarketplacePrice,
                                   ProductOzonPrice,
                                   ProfitabilityMarketplaceProduct)


# @receiver(post_save, sender=MarketplaceLogistic)
# def profitability_logistic_update(sender, instance, created, **kwargs):
#     """
#     Пересчет рентабельности при изменении стоимости логистики
#     """
#     product = instance.marketplace_product
#     try:
#         changer_profitability_calculate(product)
#     except Exception as e:
#         message = f'Не удалось обновить рентабельность для продукта при обновлении логистики: {product}. Ошибка: {e}'
#         print(message)


# @receiver(post_save, sender=MarketplaceCommission)
# def profitability_comission_update(sender, instance, created, **kwargs):
#     """
#     Пересчет рентабельности при изменении стоимости комиссии
#     """
#     product = instance.marketplace_product
#     try:
#         changer_profitability_calculate(product)
#     except Exception as e:
#         message = f'Не удалось обновить рентабельность для продукта при обновлении комиссии: {product}. Ошибка: {e}'
#         print(message)


# @receiver(post_save, sender=ProductForMarketplacePrice)
# def profitability_price_wb_ya_update(sender, instance, created, **kwargs):
#     """
#     Пересчет рентабельности при изменении цены на Яндексе и Вб
#     """
#     main_product = instance.product
#     products_list = MarketplaceProduct.objects.filter(product=main_product)
#     for product in products_list:
#         try:
#             changer_profitability_calculate(product)
#         except Exception as e:
#             message = f'Не удалось обновить рентабельность для продукта при обновлении цены: {product}. Ошибка: {e}'
#             print(message)


# @receiver(post_save, sender=ProductOzonPrice)
# def profitability_price_oz_update(sender, instance, created, **kwargs):
#     """
#     Пересчет рентабельности при изменении цены на Озоне
#     """
#     main_product = instance.product
#     products_list = MarketplaceProduct.objects.filter(product=main_product)
#     for product in products_list:
#         try:
#             changer_profitability_calculate(product)
#         except Exception as e:
#             message = f'Не удалось обновить рентабельность для продукта: {product}. Ошибка: {e}'
#             print(message)


# @receiver(post_save, sender=ProfitabilityMarketplaceProduct)
# def price_profitability_price_oz_update(sender, instance, created, **kwargs):
#     """
#     Пересчет цены на основе рентабельности при изменении Накладных расходов
#     """
#     product = instance.mp_product
#     try:
#         changer_price_with_profitability(product)
#     except Exception as e:
#         message = f'Не удалось обновить цену на основе рентабельности для продукта: {product}. Ошибка: {e}'
#         print(message)


# @receiver(post_save, sender=ProductCostPrice)
# def profitability_price_oz_update(sender, instance, created, **kwargs):
#     """
#     Пересчет цены на основе рентабельности при изменении
#     себестоимости Продукта по методу оприходования по FIFO
#     """
#     main_product = instance.product
#     products_list = MarketplaceProduct.objects.filter(product=main_product)
#     for product in products_list:
#         try:
#             changer_price_with_profitability(product)
#         except Exception as e:
#             message = f'Не удалось обновить цену на основе рентабельности для продукта: {product}. Ошибка: {e}'
#             print(message)
