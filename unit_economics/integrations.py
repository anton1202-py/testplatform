import asyncio
import logging
import traceback
from functools import wraps

import requests
# import telegram
from asgiref.sync import sync_to_async
from django.db.models import Count, Q

from analyticalplatform.settings import ADMINS_CHATID_LIST, TELEGRAM_TOKEN
from api_requests.moy_sklad import change_product_price
from core.enums import MarketplaceChoices
from core.models import Account, Platform, User
from unit_economics.models import (MarketplaceAction, MarketplaceCategory,
                                   MarketplaceCommission, MarketplaceLogistic,
                                   MarketplaceProduct,
                                   MarketplaceProductPriceWithProfitability,
                                   ProductCostPrice,
                                   ProductForMarketplacePrice,
                                   ProductOzonPrice, ProductPrice,
                                   ProfitabilityMarketplaceProduct)
from unit_economics.serializers import MarketplaceProductSerializer

logger = logging.getLogger(__name__)
# bot = telegram.Bot(token=TELEGRAM_TOKEN)


# def sender_error_to_tg(func):
#     async def async_wrapper(*args, **kwargs):
#         try:
#             return await func(*args, **kwargs)
#         except Exception as e:
#             tb_str = traceback.format_exc()
#             message_error = (f'Ошибка в функции: {func.__name__}\n'
#                              f'Функция выполняет: {func.__doc__}\n'
#                              f'Ошибка\n: {e}\n\n'
#                              f'Техническая информация:\n {tb_str}')
#             for chat_id in ADMINS_CHATID_LIST:
#                 await bot.send_message(chat_id=chat_id, text=message_error[:4000])

#     def sync_wrapper(*args, **kwargs):
#         # Запускаем асинхронную функцию через asyncio.run
#         return asyncio.run(async_wrapper(*args, **kwargs))

#     # Проверяем, является ли функция асинхронной
#     if asyncio.iscoroutinefunction(func):
#         return async_wrapper
#     else:
#         return sync_wrapper


# @sender_error_to_tg
def add_marketplace_product_to_db(
        account_sklad, barcode,
        account, platform, name,
        sku, seller_article, category_number,
        category_name, width,
        height, length, weight, ozon_sku=''):
    """
    Записывает данные о продуктах маркетплейсов после сопоставления с основными продуктами в базу данных
    """
    category_obj, created = MarketplaceCategory.objects.get_or_create(
        platform=platform,
        category_number=category_number,
        category_name=category_name
    )
    product_data = ProductPrice.objects.filter(account=account_sklad)
    objects_for_create = []
    for product in product_data:
        bc_list = product.barcode
        if str(barcode) in bc_list:
            if not MarketplaceProduct.objects.filter(account=account, platform=platform, product=product, sku=sku, barcode=barcode):
                product_obj = MarketplaceProduct(
                    account=account,
                    platform=platform,
                    product=product,
                    name=name,
                    sku=sku,
                    seller_article=seller_article,
                    barcode=barcode,
                    category=category_obj,
                    width=width,
                    height=height,
                    length=length,
                    weight=weight,
                    ozonsku=ozon_sku
                )
                objects_for_create.append(product_obj)
            else:
                MarketplaceProduct.objects.filter(account=account, platform=platform, product=product, sku=sku, barcode=barcode).update(
                    name=name,
                    seller_article=seller_article,
                    category=category_obj,
                    width=width,
                    height=height,
                    length=length,
                    weight=weight,
                    ozonsku=ozon_sku
                )
        continue
    MarketplaceProduct.objects.bulk_create(objects_for_create)


# @sender_error_to_tg
def add_marketplace_comission_to_db(
        product_obj, fbs_commission=None, fbo_commission=None, dbs_commission=None, fbs_express_commission=None):
    """
    Записывает комиссии маркетплейсов в базу данных
    """
    search_params = {'marketplace_product': product_obj}
    values_for_update = {
        "fbs_commission": fbs_commission,
        "fbo_commission": fbo_commission,
        "dbs_commission": dbs_commission,
        "fbs_express_commission": fbs_express_commission
    }
    MarketplaceCommission.objects.update_or_create(
        defaults=values_for_update, **search_params)


# @sender_error_to_tg
def add_marketplace_logistic_to_db(
        product_obj, cost_logistic=None, cost_logistic_fbo=None, cost_logistic_fbs=None):
    """
    Записывает затраты на логистику маркетплейсов в базу данных
    """
    search_params = {'marketplace_product': product_obj}
    values_for_update = {
        "cost_logistic": cost_logistic,
        "cost_logistic_fbo": cost_logistic_fbo,
        "cost_logistic_fbs": cost_logistic_fbs
    }
    MarketplaceLogistic.objects.update_or_create(
        defaults=values_for_update, **search_params)


# def profitability_calculate(user_id, overheads=0.2):
#     """Расчет рентабельности по изменению для всей таблицы"""
#     user = User.objects.get(id=user_id)
#     mp_products_list = MarketplaceProduct.objects.filter(account__user=user).select_related(
#         'marketproduct_logistic', 'marketproduct_comission', 'product', 'platform', 'account')
#     products_to_update = []
#     products_to_create = []
#     for product in mp_products_list:
#         try:
#             if product.platform.name == 'OZON':
#                 account = product.account
#                 price = ProductOzonPrice.objects.get(
#                     account=account, product=product.product).ozon_price
#                 comission = product.marketproduct_comission.fbs_commission if hasattr(product, 'marketproduct_comission') else 0
#                 logistic_cost = product.marketproduct_logistic.cost_logistic_fbs if hasattr(product, 'marketproduct_logistic') else 0
#             elif product.platform.name == 'Wildberries':
#                 price = ProductForMarketplacePrice.objects.get(
#                     product=product.product).wb_price
#                 comission = product.marketproduct_comission.fbs_commission if hasattr(product, 'marketproduct_comission') else 0
#                 logistic_cost = product.marketproduct_logistic.cost_logistic if hasattr(product, 'marketproduct_logistic') else 0
#             elif product.platform.name == 'Яндекс Маркет':
#                 price = ProductForMarketplacePrice.objects.get(
#                     product=product.product).yandex_price
#                 comission = product.marketproduct_comission.fbs_commission if hasattr(product, 'marketproduct_comission') else 0
#                 logistic_cost = product.marketproduct_logistic.cost_logistic if hasattr(product, 'marketproduct_logistic') else 0
#             else:
#                 continue  # Пропускаем неизвестные платформы
#
#             product_cost_price = product.product.cost_price/100
#
#             if price > 0:
#                 search_params = {'mp_product': product}
#                 try:
#                     profitability_product = ProfitabilityMarketplaceProduct.objects.get(
#                         **search_params)
#                     overheads = profitability_product.overheads
#                 except ProfitabilityMarketplaceProduct.DoesNotExist:
#                     overheads = overheads
#                 profit = round((price - float(product_cost_price) -
#                                 logistic_cost - comission - (overheads * price)), 2)
#                 profitability = round(((profit / price) * 100), 2)
#
#                 values_for_update = {
#                     "profit": profit,
#                     "profitability": profitability
#                 }
#                 if 'profitability_product' in locals():
#                     # Обновляем существующий объект
#                     profitability_product.profit = profit
#                     profitability_product.profitability = profitability
#                     products_to_update.append(profitability_product)
#                 else:
#                     # Создаем новый объект
#                     products_to_create.append(ProfitabilityMarketplaceProduct(
#                         mp_product=product, **values_for_update))
#         except (ProductOzonPrice.DoesNotExist, ProductForMarketplacePrice.DoesNotExist):
#             # Пропускаем продукты, для которых нет цены
#             continue
#
#     if products_to_update:
#         ProfitabilityMarketplaceProduct.objects.bulk_update(
#             products_to_update, ['profit', 'profitability'])
#
#     if products_to_create:
#         ProfitabilityMarketplaceProduct.objects.bulk_create(products_to_create)
#
#     result = ProfitabilityMarketplaceProduct.objects.aggregate(
#         count_above_20=Count('id', filter=Q(profitability__gt=20)),
#         count_between_10_and_20=Count('id', filter=Q(
#             profitability__lt=20) & Q(profitability__gt=10)),
#         count_between_0_and_10=Count('id', filter=Q(
#             profitability__gt=0) & Q(profitability__lt=10)),
#         count_between_0_and_minus_10=Count('id', filter=Q(
#             profitability__lt=0) & Q(profitability__gt=-10)),
#         count_between_minus10_and_minus_20=Count('id', filter=Q(
#             profitability__gt=-20) & Q(profitability__lt=-10)),
#         count_below_minus_20=Count('id', filter=Q(profitability__lt=-20)),
#     )
#     return result


def profitability_calculate(user_id, overheads=0.2, profitability_group=None):
    """Расчет рентабельности по изменению для всей таблицы"""
    user = User.objects.get(id=user_id)
    mp_products_list = MarketplaceProduct.objects.filter(account__user=user).select_related(
        'marketproduct_logistic', 'marketproduct_comission', 'product', 'platform', 'account')
    products_to_update = []
    products_to_create = []
    filtered_products = []

    for product in mp_products_list:
        try:
            if product.platform.name == 'OZON':
                account = product.account
                price = ProductOzonPrice.objects.get(
                    account=account, product=product.product).ozon_price
                comission = product.marketproduct_comission.fbs_commission if hasattr(
                    product, 'marketproduct_comission') else 0
                logistic_cost = product.marketproduct_logistic.cost_logistic_fbs if hasattr(
                    product, 'marketproduct_logistic') else 0
            elif product.platform.name == 'Wildberries':
                price = ProductForMarketplacePrice.objects.get(
                    product=product.product).wb_price
                comission = product.marketproduct_comission.fbs_commission if hasattr(
                    product, 'marketproduct_comission') else 0
                logistic_cost = product.marketproduct_logistic.cost_logistic if hasattr(
                    product, 'marketproduct_logistic') else 0
            elif product.platform.name == 'Яндекс Маркет':
                price = ProductForMarketplacePrice.objects.get(
                    product=product.product).yandex_price
                comission = product.marketproduct_comission.fbs_commission if hasattr(
                    product, 'marketproduct_comission') else 0
                logistic_cost = product.marketproduct_logistic.cost_logistic if hasattr(
                    product, 'marketproduct_logistic') else 0
            else:
                continue  # Пропускаем неизвестные платформы

            product_cost_price = product.product.cost_price

            if price > 0:
                search_params = {'mp_product': product}
                try:
                    profitability_product = ProfitabilityMarketplaceProduct.objects.get(
                        **search_params)
                    overheads = profitability_product.overheads
                except ProfitabilityMarketplaceProduct.DoesNotExist:
                    overheads = overheads
                profit = round((price - float(product_cost_price) -
                                logistic_cost - comission - (overheads * price)), 2)
                # print(product, 'profit', profit, 'price', price,
                #       'product_cost_price', product_cost_price, 'logistic_cost', logistic_cost, 'comission', comission,  product.platform)
                profitability = round(((profit / price) * 100), 2)

                # Добавляем фильтрацию по группе рентабельности

                values_for_update = {
                    "profit": profit,
                    "profitability": profitability
                }
                if 'profitability_product' in locals():
                    # Обновляем существующий объект
                    profitability_product.profit = profit
                    profitability_product.profitability = profitability
                    products_to_update.append(profitability_product)
                else:
                    # Создаем новый объект
                    products_to_create.append(ProfitabilityMarketplaceProduct(
                        mp_product=product, **values_for_update))
        except (ProductOzonPrice.DoesNotExist, ProductForMarketplacePrice.DoesNotExist):
            # Пропускаем продукты, для которых нет цены
            continue

    if products_to_update:
        ProfitabilityMarketplaceProduct.objects.bulk_update(
            products_to_update, ['profit', 'profitability'])

    if products_to_create:
        ProfitabilityMarketplaceProduct.objects.bulk_create(products_to_create)

    result = ProfitabilityMarketplaceProduct.objects.aggregate(
        count_above_20=Count('id', filter=Q(profitability__gt=20)),
        count_between_10_and_20=Count('id', filter=Q(
            profitability__lte=20) & Q(profitability__gt=10)),
        count_between_0_and_10=Count('id', filter=Q(
            profitability__lte=10) & Q(profitability__gt=0)),
        count_between_0_and_minus_10=Count('id', filter=Q(
            profitability__lte=0) & Q(profitability__gt=-10)),
        count_between_minus10_and_minus_20=Count('id', filter=Q(
            profitability__lte=-10) & Q(profitability__gt=-20)),
        count_below_minus_20=Count('id', filter=Q(profitability__lte=-20)),
    )
    if profitability_group:
        mp_products_list = MarketplaceProduct.objects.filter(
            account__user=user)
        for product in mp_products_list:
            if ProfitabilityMarketplaceProduct.objects.filter(
                    mp_product=product).exists():
                profitability = ProfitabilityMarketplaceProduct.objects.get(
                    mp_product=product).profitability
                if profitability_group == 'count_above_20' and profitability > 20:
                    filtered_products.append(product)
                elif profitability_group == 'count_between_10_and_20' and 10 < profitability <= 20:
                    filtered_products.append(product)
                elif profitability_group == 'count_between_0_and_10' and 0 < profitability <= 10:
                    filtered_products.append(product)
                elif profitability_group == 'count_between_0_and_minus_10' and -10 < profitability <= 0:
                    filtered_products.append(product)
                elif profitability_group == 'count_between_minus10_and_minus_20' and -20 < profitability <= -10:
                    filtered_products.append(product)
                elif profitability_group == 'count_below_minus_20' and profitability <= -20:
                    filtered_products.append(product)
        result['filtered_products'] = filtered_products

    return result


# @sender_error_to_tg
# def profitability_calculate(user_id, overheads=0.2):
#     """Расчет рентабельности по изменению для всей таблицы"""
#     user = User.objects.get(id=user_id)
#     mp_products_list = MarketplaceProduct.objects.filter(account__user=user).select_related(
#         'marketproduct_logistic').select_related('marketproduct_comission')
#     products_to_update = []
#     products_to_create = []
#     products_by_profitability = {
#         'above_20': [],
#         'between_10_and_20': [],
#         'between_0_and_10': [],
#         'between_0_and_minus_10': [],
#         'between_minus10_and_minus_20': [],
#         'below_minus_20': []
#     }
#
#     for product in mp_products_list:
#         try:
#             if product.platform.name == 'OZON':
#                 account = product.account
#                 price = ProductOzonPrice.objects.get(
#                     account=account, product=product.product).ozon_price
#                 comission = product.marketproduct_comission.fbs_commission
#                 logistic_cost = product.marketproduct_logistic.cost_logistic_fbs
#             elif product.platform.name == 'Wildberries':
#                 price = ProductForMarketplacePrice.objects.get(
#                     product=product.product).wb_price
#                 comission = product.marketproduct_comission.fbs_commission
#                 logistic_cost = product.marketproduct_logistic.cost_logistic
#             elif product.platform.name == 'Яндекс Маркет':
#                 price = ProductForMarketplacePrice.objects.get(
#                     product=product.product).yandex_price
#                 comission = product.marketproduct_comission.fbs_commission
#                 logistic_cost = product.marketproduct_logistic.cost_logistic
#             product_cost_price = product.product.cost_price / 100
#
#             if price > 0:
#                 search_params = {'mp_product': product}
#                 try:
#                     profitability_product = ProfitabilityMarketplaceProduct.objects.get(
#                         **search_params)
#                     overheads = profitability_product.overheads
#                 except ProfitabilityMarketplaceProduct.DoesNotExist:
#                     overheads = overheads
#                 profit = round((price - float(product_cost_price) -
#                                 logistic_cost - comission - (overheads * price)), 2)
#                 profitability = round(((profit / price) * 100), 2)
#
#                 values_for_update = {
#                     "profit": profit,
#                     "profitability": profitability
#                 }
#                 if 'profitability_product' in locals():
#                     # Обновляем существующий объект
#                     profitability_product.profit = profit
#                     profitability_product.profitability = profitability
#                     products_to_update.append(profitability_product)
#                 else:
#                     # Создаем новый объект
#                     products_to_create.append(ProfitabilityMarketplaceProduct(
#                         mp_product=product, **values_for_update))
#
#                 # Добавляем товар в соответствующую категорию рентабельности
#                 if profitability > 20:
#                     products_by_profitability['above_20'].append(product)
#                 elif 10 < profitability <= 20:
#                     products_by_profitability['between_10_and_20'].append(
#                         product)
#                 elif 0 < profitability <= 10:
#                     products_by_profitability['between_0_and_10'].append(
#                         product)
#                 elif -10 < profitability <= 0:
#                     products_by_profitability['between_0_and_minus_10'].append(
#                         product)
#                 elif -20 < profitability <= -10:
#                     products_by_profitability['between_minus10_and_minus_20'].append(
#                         product)
#                 elif profitability <= -20:
#                     products_by_profitability['below_minus_20'].append(product)
#         except MarketplaceProduct.marketproduct_comission.RelatedObjectDoesNotExist:
#             # Пропускаем товар, если нет связанного marketproduct_comission
#             continue
#
#     if products_to_update:
#         ProfitabilityMarketplaceProduct.objects.bulk_update(
#             products_to_update, ['profit', 'profitability'])
#
#     if products_to_create:
#         ProfitabilityMarketplaceProduct.objects.bulk_create(products_to_create)
#
#     result = ProfitabilityMarketplaceProduct.objects.aggregate(
#         count_above_20=Count('id', filter=Q(profitability__gt=20)),
#         count_between_10_and_20=Count('id', filter=Q(
#             profitability__lt=20) & Q(profitability__gt=10)),
#         count_between_0_and_10=Count('id', filter=Q(
#             profitability__gt=0) & Q(profitability__lt=10)),
#         count_between_0_and_minus_10=Count('id', filter=Q(
#             profitability__lt=0) & Q(profitability__gt=-10)),
#         count_between_minus10_and_minus_20=Count('id', filter=Q(
#             profitability__gt=-20) & Q(profitability__lt=-10)),
#         count_below_minus_20=Count('id', filter=Q(profitability__lt=-20)),
#     )
#
#     # Сериализация товаров
#     serialized_products_by_profitability = {
#         key: MarketplaceProductSerializer(products, many=True).data
#         for key, products in products_by_profitability.items()
#     }
#
#     result['products_by_profitability'] = serialized_products_by_profitability
#     return result


# @sender_error_to_tg
def save_overheds_for_mp_product(mp_product_dict: dict):
    """
    Сохраняет рентабельность для каждого продукта

    Входящие данные:
        mp_product_dict: словарь типа {mp_product_id: product_overheads}
        mp_product_id - id продлукта из таблицы MarketplaceProduct
        product_overheads - накладные расходы в формате float (например 0.2)
    """
    for mp_product_id, product_overheads in mp_product_dict.items():
        product_obj = MarketplaceProduct.objects.get(id=mp_product_id)
        profitability_obj = ProfitabilityMarketplaceProduct.objects.get(
            mp_product=product_obj)
        profitability_obj.overheads = product_overheads
        profitability_obj.save()


# @sender_error_to_tg
def calculate_mp_price_with_profitability(user_id):
    """Расчет цены товара на маркетплейсе на основе рентабельности"""
    user = User.objects.get(id=user_id)
    mp_products_list = MarketplaceProduct.objects.filter(account__user=user).select_related(
        'marketproduct_logistic').select_related('marketproduct_comission').select_related('mp_profitability')
    products_to_update = []
    products_to_create = []
    for prod in mp_products_list:
        x = MarketplaceCommission.objects.filter(marketplace_product=prod)
        if len(x) == 0:
            print('нет комиссии', prod)
    for product in mp_products_list:
        if MarketplaceCommission.objects.filter(marketplace_product=prod).exists():
            if product.platform.name == 'OZON':
                comission = product.marketproduct_comission.fbs_commission
                logistic_cost = product.marketproduct_logistic.cost_logistic_fbs
            else:
                comission = product.marketproduct_comission.fbs_commission
                logistic_cost = product.marketproduct_logistic.cost_logistic
            if ProfitabilityMarketplaceProduct.objects.filter(mp_product=product).exists():
                overheads = product.mp_profitability.overheads
                profitability = product.mp_profitability.profitability
                common_product_cost_price = product.product.cost_price/100
                if ProductCostPrice.objects.filter(
                        product=product.product).exists():
                    profit_product_cost_price = ProductCostPrice.objects.get(
                        product=product.product).cost_price
                else:
                    profit_product_cost_price = 0

                # Цена на основе обычной себестоимости (на основе себестоимости комплектов)
                common_price = round(((common_product_cost_price/100 + comission + logistic_cost +
                                       common_product_cost_price/100) / (1 - profitability/100 - overheads)), 2)

                # Цена на основе себестоимости по оприходованию
                enter_price = round(((profit_product_cost_price + comission + logistic_cost +
                                      profit_product_cost_price) / (1 - profitability/100 - overheads)), 2)
                search_params = {'mp_product': product}
                try:
                    mp_product_price = MarketplaceProductPriceWithProfitability.objects.get(
                        **search_params)

                except MarketplaceProductPriceWithProfitability.DoesNotExist:
                    pass

                values_for_update = {
                    "profit_price": enter_price,
                    "usual_price": common_price
                }
                if 'mp_product_price' in locals():
                    # Обновляем существующий объект
                    mp_product_price.profit_price = enter_price
                    mp_product_price.usual_price = common_price
                    products_to_update.append(mp_product_price)
                else:
                    # Создаем новый объект
                    products_to_create.append(MarketplaceProductPriceWithProfitability(
                        mp_product=product, **values_for_update))
    if products_to_update:
        MarketplaceProductPriceWithProfitability.objects.bulk_update(
            products_to_update, ['profit_price', 'usual_price'])

    if products_to_create:
        MarketplaceProductPriceWithProfitability.objects.bulk_create(
            products_to_create)


def calculate_mp_price_with_incoming_profitability(incoming_profitability: float, product_list: list):
    """
    Расчет цены товара на маркетплейсе на основе рентабельности.
    Если рентабельность товара в базе данных меньше, чем входящая рентабельность,
    то цена пересчитвается, если больше или равно, то не изменяется

    Входящие данные:
        incoming_profitability - входящая рентабельность с которой сравниваем рентабельность из БД
        product_list - список товаров, которые находятся на странице

    Возвращает: 
        mp_products_list - список объектов модели MarketplaceProduct

    """
    products_to_update = []
    products_to_create = []
    for mp_product in product_list:
        mp_products_list = MarketplaceProduct.objects.filter(id=mp_product.id).select_related(
            'marketproduct_logistic').select_related('marketproduct_comission').select_related('mp_profitability')

        for product in mp_products_list:

            if product.platform.name == 'OZON':
                if MarketplaceCommission.objects.filter(marketplace_product=product).exists():
                    comission = product.marketproduct_comission.fbs_commission
                else:
                    comission = 0
                if MarketplaceLogistic.objects.filter(marketplace_product=product).exists():
                    logistic_cost = product.marketproduct_logistic.cost_logistic_fbs
                else:
                    comission = 0
            else:
                comission = product.marketproduct_comission.fbs_commission
                logistic_cost = product.marketproduct_logistic.cost_logistic
            if ProfitabilityMarketplaceProduct.objects.filter(mp_product=product).exists():
                overheads = product.mp_profitability.overheads
                profitability = product.mp_profitability.profitability
                common_product_cost_price = product.product.cost_price/100
                if ProductCostPrice.objects.filter(
                        product=product.product).exists():
                    profit_product_cost_price = ProductCostPrice.objects.get(
                        product=product.product).cost_price
                else:
                    profit_product_cost_price = 0

                if incoming_profitability > profitability:
                    profitability = incoming_profitability
                # Цена на основе обычной себестоимости (на основе себестоимости комплектов)
                    common_price = round(((common_product_cost_price + comission + logistic_cost
                                           ) / (1 - profitability - overheads)), 2)

                    # Цена на основе себестоимости по оприходованию
                    enter_price = round(((profit_product_cost_price + comission + logistic_cost
                                          ) / (1 - profitability - overheads)), 2)
                    search_params = {'mp_product': product}
                    try:
                        mp_product_price = MarketplaceProductPriceWithProfitability.objects.get(
                            **search_params)

                    except MarketplaceProductPriceWithProfitability.DoesNotExist:
                        pass

                    values_for_update = {
                        "profit_price": enter_price,
                        "usual_price": common_price
                    }
                    if 'mp_product_price' in locals():
                        # Обновляем существующий объект
                        mp_product_price.profit_price = enter_price
                        mp_product_price.usual_price = common_price
                        products_to_update.append(mp_product_price)
                    else:
                        # Создаем новый объект
                        products_to_create.append(MarketplaceProductPriceWithProfitability(
                            mp_product=product, **values_for_update))
    if products_to_update:
        MarketplaceProductPriceWithProfitability.objects.bulk_update(
            products_to_update, ['profit_price', 'usual_price'])
    if products_to_create:
        MarketplaceProductPriceWithProfitability.objects.bulk_create(
            products_to_create)
    return product_list


def update_price_info_from_user_request(data_dict: dict):
    """
    Обновляет цены на Мой склад и в БД, если пользователь отправил запрос
    {
        'user_id': user_id.
        'account_id': account_id,
        'platform_name': platform_name,
        'products_data': [
            {
                'marketplaceproduct_id': marketplaceproduct_id,
                'new_price': new_price,
                'overhead': overhead
            }
        ]
    }
    """

    user_id = data_dict.get('user_id', '')
    account_id = data_dict.get('account_id', '')
    platform_name = data_dict.get('platform_name', '')
    products_data = data_dict.get('products_data', '')

    for data in products_data:
        marketplaceproduct_id = data.get('marketplaceproduct_id', '')
        new_price = data.get('new_price', '')
        overhead = data.get('overhead', '')
        mp_product_obj = MarketplaceProduct.objects.get(
            id=marketplaceproduct_id)
        product_obj = mp_product_obj.product
        account_obj = Account.objects.get(id=account_id)
        moy_sklad_account = Account.objects.get(
            user=User.objects.get(id=user_id),
            platform=Platform.objects.get(
                platform_type=MarketplaceChoices.MOY_SKLAD)
        )
        moy_sklad_token = moy_sklad_account.authorization_fields['token']
        if overhead:
            profitability_obj = ProfitabilityMarketplaceProduct.objects.get(
                mp_product=mp_product_obj)
            profitability_obj.overheads = overhead
            profitability_obj.save()
            changer_profitability_calculate(profitability_obj.mp_product)
        if new_price:
            productprice_obj = ProductForMarketplacePrice.objects.get(
                product=product_obj)
            if platform_name == 'Wildberries':
                productprice_obj.wb_price = new_price
                productprice_obj.save()
            if platform_name == 'Yandex Market':
                productprice_obj.yandex_price = new_price
                productprice_obj.save()
            if platform_name == 'OZON':
                ozonproductprice_obj = ProductOzonPrice.objects.get(
                    product=product_obj, account=account_obj)
                ozonproductprice_obj.ozon_price = new_price
                ozonproductprice_obj.save()
            account_name = Account.objects.get(id=account_id).name
            if product_obj.moy_sklad_product_number:
                change_product_price(moy_sklad_token, platform_name, account_name,
                                     new_price, product_obj.moy_sklad_product_number)
                mp_product_obj.change_price_flag = True
                mp_product_obj.save()
            else:
                message = f"У продукта {product_obj.name} не могу обновить цену на {platform_name} {account_name}. В БД не нашел его ID с Мой склад"
                # for chat_id in ADMINS_CHATID_LIST:
                #     bot.send_message(chat_id=chat_id, text=message[:4000])


def changer_profitability_calculate(product):
    """
    Вспомогательная функция для подсчета рентабельности.
    Применяется в сигналах изменения различных моделей

    Входящие данные:
    product - объект модели MarketplaceProduct
    """
    price = 0
    if product.platform.name == 'OZON':
        account = product.account
        price = ProductOzonPrice.objects.get(
            account=account, product=product.product).ozon_price
        comission = product.marketproduct_comission.fbs_commission
        logistic_cost = product.marketproduct_logistic.cost_logistic_fbs
    elif product.platform.name == 'Wildberries':
        price = ProductForMarketplacePrice.objects.get(
            product=product.product).wb_price
        comission = product.marketproduct_comission.fbs_commission
        logistic_cost = product.marketproduct_logistic.cost_logistic
    elif product.platform.name == 'Yandex Market':
        price = ProductForMarketplacePrice.objects.get(
            product=product.product).yandex_price
        comission = product.marketproduct_comission.fbs_commission
        logistic_cost = product.marketproduct_logistic.cost_logistic
    product_cost_price = product.product.cost_price
    if price > 0:
        search_params = {'mp_product': product}
        try:
            profitability_product = ProfitabilityMarketplaceProduct.objects.get(
                **search_params)
            overheads = profitability_product.overheads
        except ProfitabilityMarketplaceProduct.DoesNotExist:
            overheads = 0.2
        profit = round((price - float(product_cost_price) -
                        logistic_cost - comission - (overheads * price)), 2)
        profitability = round(((profit / price) * 100), 2)
        values_for_update = {
            "profit": profit,
            "profitability": profitability
        }
        ProfitabilityMarketplaceProduct.objects.update_or_create(
            defaults=values_for_update, **search_params)


def changer_price_with_profitability(product):
    """
    Вспомогательная функция для подсчета цены на основе рентабельности.
    Применяется в сигналах изменения различных моделей

    Входящие данные:
    product - объект модели MarketplaceProduct
    """
    if product.platform.name == 'OZON':
        comission = product.marketproduct_comission.fbs_commission
        logistic_cost = product.marketproduct_logistic.cost_logistic_fbs
    else:
        comission = product.marketproduct_comission.fbs_commission
        logistic_cost = product.marketproduct_logistic.cost_logistic
    if ProfitabilityMarketplaceProduct.objects.filter(mp_product=product).exists():
        overheads = product.mp_profitability.overheads
        profitability = product.mp_profitability.profitability
        common_product_cost_price = product.product.cost_price/100
        if ProductCostPrice.objects.filter(
                product=product.product).exists():
            profit_product_cost_price = ProductCostPrice.objects.get(
                product=product.product).cost_price
        else:
            profit_product_cost_price = 0
        # Цена на основе обычной себестоимости (на основе себестоимости комплектов)
        common_price = round(((common_product_cost_price/100 + comission + logistic_cost +
                               common_product_cost_price/100) / (1 - profitability/100 - overheads)), 2)
        # Цена на основе себестоимости по оприходованию
        enter_price = round(((profit_product_cost_price + comission + logistic_cost +
                              profit_product_cost_price) / (1 - profitability/100 - overheads)), 2)
        search_params = {'mp_product': product}

        values_for_update = {
            "profit_price": enter_price,
            "usual_price": common_price
        }
        MarketplaceProductPriceWithProfitability.objects.update_or_create(
            defaults=values_for_update, **search_params)
