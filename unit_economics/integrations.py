import asyncio
import logging
import traceback
from functools import wraps

import requests
from asgiref.sync import sync_to_async
from django.db.models import Count, Prefetch, Q, Case, When, Value, BooleanField, Sum, F
import telegram

from analyticalplatform.settings import ADMINS_CHATID_LIST, TELEGRAM_TOKEN
from api_requests.moy_sklad import change_product_price
from core.enums import MarketplaceChoices
from core.models import Account, Platform, User
from unit_economics.models import (MarketplaceAction, MarketplaceCategory,
                                   MarketplaceCommission, MarketplaceLogistic,
                                   MarketplaceProduct, MarketplaceProductInAction,
                                   MarketplaceProductPriceWithProfitability,
                                   ProductCostPrice,
                                   ProductForMarketplacePrice,
                                   ProductOzonPrice, ProductPrice,
                                   ProfitabilityMarketplaceProduct, StoreOverhead)
from unit_economics.serializers import MarketplaceProductSerializer

logger = logging.getLogger(__name__)

async def send_message_async(chat_id, message):
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=chat_id, text=message[:4000])

def sender_error_to_tg(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            tb_str = traceback.format_exc()
            message_error = (f'Ошибка в функции: {func.__name__}\n'
                             f'Функция выполняет: {func.__doc__}\n'
                             f'Ошибка\n: {e}\n\n'
                             f'Техническая информация:\n {tb_str}')
            for chat_id in ADMINS_CHATID_LIST:
                asyncio.run(send_message_async(chat_id, message_error))
    return wrapper


@sender_error_to_tg
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
                MarketplaceProduct(
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
                ).save()
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

@sender_error_to_tg
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


@sender_error_to_tg
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


def profitability_part_template(product):
    """
    Шаблон для расчета рентабельности
    """
    comission_logistic_costs = {}
    account_obj = product.account
    overheads = 0.2
    overhead_data = StoreOverhead.objects.filter(account=account_obj).aggregate(
        overhead_sum=Sum('overhead'))
    if overhead_data['overhead_sum']:
        overheads = overhead_data['overhead_sum'] / 100
    
    if product.platform.name == 'OZON':
        account = product.account
        price = ProductOzonPrice.objects.get(
            account=account, product=product.product).ozon_price
        comission_fbs = product.marketproduct_comission.fbs_commission if hasattr(
            product, 'marketproduct_comission') else 0
        comission_fbo = product.marketproduct_comission.fbo_commission if hasattr(
            product, 'marketproduct_comission') else 0
        comission_dbs = product.marketproduct_comission.dbs_commission if hasattr(
            product, 'marketproduct_comission') else 0
        comission_fbs_express = product.marketproduct_comission.fbs_express_commission if hasattr(
            product, 'marketproduct_comission') else 0
        logistic_cost_fbs = product.marketproduct_logistic.cost_logistic_fbs if hasattr(
            product, 'marketproduct_logistic') else 0
        logistic_cost_fbo = product.marketproduct_logistic.cost_logistic_fbo if hasattr(
            product, 'marketproduct_logistic') else 0
        comission_logistic_costs = {
            'fbo': {
                'logistic_cost': logistic_cost_fbo,
                'comission': comission_fbo
            },
            'fbs': {
                'logistic_cost': logistic_cost_fbs,
                'comission': comission_fbs
            },
            'dbs': {
                'logistic_cost': 0,
                'comission': comission_dbs
            },
            'fbs_express': {
                'logistic_cost': 0,
                'comission': comission_fbs_express
            }
        }
    elif product.platform.name == 'Wildberries':
        price = ProductForMarketplacePrice.objects.get(
            product=product.product).wb_price
        comission_fbs = product.marketproduct_comission.fbs_commission if hasattr(
            product, 'marketproduct_comission') else 0
        comission_fbo = product.marketproduct_comission.fbo_commission if hasattr(
            product, 'marketproduct_comission') else 0
        comission_dbs = product.marketproduct_comission.dbs_commission if hasattr(
            product, 'marketproduct_comission') else 0
        comission_fbs_express = product.marketproduct_comission.fbs_express_commission if hasattr(
            product, 'marketproduct_comission') else 0
        logistic_cost = product.marketproduct_logistic.cost_logistic if hasattr(
            product, 'marketproduct_logistic') else 0
        comission_logistic_costs = {
            'fbo': {
                'logistic_cost': logistic_cost,
                'comission': comission_fbo
            },
            'fbs': {
                'logistic_cost': logistic_cost,
                'comission': comission_fbs
            },
            'dbs': {
                'logistic_cost': logistic_cost,
                'comission': comission_dbs
            },
            'fbs_express': {
                'logistic_cost': logistic_cost,
                'comission': comission_fbs_express
            }
        }
    elif product.platform.name == 'Yandex Market':
        price = ProductForMarketplacePrice.objects.get(
            product=product.product).yandex_price
        comission_fbs = product.marketproduct_comission.fbs_commission if hasattr(
            product, 'marketproduct_comission') else 0
        comission_fbo = product.marketproduct_comission.fbo_commission if hasattr(
            product, 'marketproduct_comission') else 0
        comission_dbs = product.marketproduct_comission.dbs_commission if hasattr(
            product, 'marketproduct_comission') else 0
        comission_fbs_express = product.marketproduct_comission.fbs_express_commission if hasattr(
            product, 'marketproduct_comission') else 0
        logistic_cost = product.marketproduct_logistic.cost_logistic if hasattr(
            product, 'marketproduct_logistic') else 0
        comission_logistic_costs = {
            'fbo': {
                'logistic_cost': logistic_cost,
                'comission': comission_fbo
            },
            'fbs': {
                'logistic_cost': logistic_cost,
                'comission': comission_fbs
            },
            'dbs': {
                'logistic_cost': logistic_cost,
                'comission': comission_dbs
            },
            'fbs_express': {
                'logistic_cost': logistic_cost,
                'comission': comission_fbs_express
            }
        }
    return price, overheads, comission_logistic_costs

def profitability_calculate_only(queryset, costprice_flag='table', order_delivery_type='fbo'):
    """
    Пересчет рентабельности для всех входящих товаров.
    Происходит, когда переключатель Цена находится на Мой Склад
    Срабатывает от ключа в фильтрах: price_toggle
    """
    if order_delivery_type == None:
        order_delivery_type = 'fbo'
    mp_products_list = queryset.select_related(
        'marketproduct_logistic', 'marketproduct_comission', 'product', 'platform', 'account')
    products_to_update = []
    products_to_create = []
    comission_logistic_costs = {}
    for product in mp_products_list:
        try:
            price, overheads, comission_logistic_costs = profitability_part_template(product)
            logistic_cost = comission_logistic_costs[order_delivery_type]['logistic_cost']
            comission = comission_logistic_costs[order_delivery_type]['comission']
            cost_price = 0

            if costprice_flag == 'table':
                cost_price = product.product.cost_price
            elif costprice_flag == 'enter':
                if ProductCostPrice.objects.filter(
                        product=product.product).exists():
                    cost_price = ProductCostPrice.objects.get(
                        product=product.product).cost_price
                else:
                    cost_price = 0

            if price > 0:
                if not comission:
                    comission = 0            
                profitability_product = ProfitabilityMarketplaceProduct.objects.filter(
                    mp_product=product)
                profit = round((price - float(cost_price) -
                                logistic_cost - (comission * price/100) - (overheads * price)), 2)
                profitability = round(((profit / price) * 100), 2)                
                if profitability_product:
                    # Обновляем существующий объект
                    profitability_product = profitability_product.first()
                    profitability_product.profit = profit
                    profitability_product.profitability = profitability
                    profitability_product.save()
                else:
                    # Создаем новый объект
                    products_to_create.append(ProfitabilityMarketplaceProduct(
                        mp_product=product, profit=profit,
                    profitability=profitability))
        except (ProductOzonPrice.DoesNotExist, ProductForMarketplacePrice.DoesNotExist):
            # Пропускаем продукты, для которых нет цены
            continue

    if products_to_update:
        ProfitabilityMarketplaceProduct.objects.bulk_update(
            products_to_update, ['profit', 'profitability'])
    if products_to_create:
        ProfitabilityMarketplaceProduct.objects.bulk_create(products_to_create)
    return queryset



def profitability_calculate(user_id, profitability_group=None, costprice_flag='table', order_delivery_type='fbo'):
    """Расчет рентабельности по изменению для всей таблицы"""
    if order_delivery_type == None:
        order_delivery_type = 'fbo'
    user = User.objects.get(id=user_id)
    mp_products_list = MarketplaceProduct.objects.filter(account__user=user).select_related(
        'marketproduct_logistic', 'marketproduct_comission', 'product', 'platform', 'account')
    products_to_update = []
    products_to_create = []
    filtered_products = []
    comission_logistic_costs = {}
    for product in mp_products_list:
        try:
            price, overheads, comission_logistic_costs = profitability_part_template(product)

            logistic_cost = comission_logistic_costs[order_delivery_type]['logistic_cost']
            comission = comission_logistic_costs[order_delivery_type]['comission']
            cost_price = 0
            if costprice_flag == 'table':
                cost_price = product.product.cost_price
            elif costprice_flag == 'enter':
                if ProductCostPrice.objects.filter(
                        product=product.product).exists():
                    cost_price = ProductCostPrice.objects.get(
                        product=product.product).cost_price
                else:
                    cost_price = 0

            if price > 0:
                search_params = {'mp_product': product}
                try:
                    profitability_product = ProfitabilityMarketplaceProduct.objects.get(
                        **search_params)
                except ProfitabilityMarketplaceProduct.DoesNotExist:
                    pass
                profit = round((price - float(cost_price) -
                                logistic_cost - (comission* price/100) - (overheads * price)), 2)
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
        count_between_minus_10_and_minus_20=Count('id', filter=Q(
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
                elif profitability_group == 'count_between_minus_10_and_minus_20' and -20 < profitability <= -10:
                    filtered_products.append(product)
                elif profitability_group == 'count_below_minus_20' and profitability <= -20:
                    filtered_products.append(product)
        result['filtered_products'] = filtered_products

    return result


@sender_error_to_tg
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


@sender_error_to_tg
def calculate_mp_price_with_profitability(user_id):
    """Расчет цены товара на маркетплейсе на основе рентабельности"""
    user = User.objects.get(id=user_id)
    mp_products_list = MarketplaceProduct.objects.filter(account__user=user).select_related(
        'marketproduct_logistic').select_related('marketproduct_comission').select_related('mp_profitability')
    products_to_update = []
    products_to_create = []

    for product in mp_products_list:
        account_obj = product.account

        overhead_data = StoreOverhead.objects.filter(account=account_obj).aggregate(
            overhead_sum=Sum('overhead'))
        overheads = overhead_data['overhead_sum']/100
        if not overheads:
            overheads = 0.2
        if MarketplaceCommission.objects.filter(marketplace_product=product).exists():
            if product.platform.name == 'OZON':
                comission = product.marketproduct_comission.fbs_commission
                logistic_cost = product.marketproduct_logistic.cost_logistic_fbs
            else:
                comission = product.marketproduct_comission.fbs_commission
                logistic_cost = product.marketproduct_logistic.cost_logistic
            if ProfitabilityMarketplaceProduct.objects.filter(mp_product=product).exists():
                profitability = product.mp_profitability.profitability
                common_product_cost_price = product.product.cost_price
                if ProductCostPrice.objects.filter(
                        product=product.product).exists():
                    profit_product_cost_price = ProductCostPrice.objects.get(
                        product=product.product).cost_price
                else:
                    profit_product_cost_price = 0

                # Цена на основе обычной себестоимости (на основе себестоимости комплектов)
                common_price = round(((common_product_cost_price/100 + logistic_cost) / (1 - profitability/100 - comission/100 - overheads)), 2)

                # Цена на основе себестоимости по оприходованию
                enter_price = round(((profit_product_cost_price +  logistic_cost) / (1 - profitability/100 - comission/100 - overheads)), 2)
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


def calculate_mp_price_with_incoming_profitability(incoming_profitability: float, product_list: list, costprice_flag='table', order_delivery_type='fbo'):
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
    if order_delivery_type is None:
        order_delivery_type = 'fbo'
    incoming_profitability = incoming_profitability
    products_to_update = []
    products_to_create = []
    comission_logistic_costs = {}
    for mp_product in product_list:
        mp_products_list = MarketplaceProduct.objects.filter(id=mp_product.id).select_related(
            'marketproduct_logistic', 'marketproduct_comission', 'mp_profitability').prefetch_related(
            'product', 'product__costprice_product', 'product__price_product', 'product__ozon_price_product')
        for product in mp_products_list:
            price = 0
            common_price = 0
            enter_price = 0
            _, overheads, comission_logistic_costs = profitability_part_template(product)
            if ProfitabilityMarketplaceProduct.objects.filter(mp_product=product).exists():
                if product.platform.id == 4:
                    price = ProductOzonPrice.objects.filter(product=product.product).first().ozon_price
                else:
                    marketplace_price = ProductForMarketplacePrice.objects.filter(product=product.product).first()
                    if product.platform.id == 1:
                        price = marketplace_price.wb_price
                    elif product.platform.id == 2:
                        price = marketplace_price.yandex_price
                logistic_cost = comission_logistic_costs[order_delivery_type]['logistic_cost']
                comission = comission_logistic_costs[order_delivery_type]['comission']
                if not comission:
                    comission = 0
                profitability = ProfitabilityMarketplaceProduct.objects.get(mp_product=product).profitability
                common_product_cost_price = product.product.cost_price
                if ProductCostPrice.objects.filter(
                        product=product.product).exists():
                    profit_product_cost_price = ProductCostPrice.objects.get(
                        product=product.product).cost_price
                else:
                    profit_product_cost_price = 0
                if not profitability:
                    profitability = 0
                elif incoming_profitability >= profitability:
                    profitability = incoming_profitability
                    # Цена на основе обычной себестоимости
                    common_price = round(((common_product_cost_price + logistic_cost
                                           ) / (1 - profitability / 100 - comission / 100 - overheads)), 2)
                    # Цена на основе себестоимости по оприходованию
                    enter_price = round(((profit_product_cost_price + logistic_cost
                                          ) / (1 - profitability / 100 - comission / 100 - overheads)), 2)
                elif incoming_profitability < profitability:
                    enter_price = price
                    common_price = price
                profit_obj = ProfitabilityMarketplaceProduct.objects.get(mp_product=product)
                profit = 0
                if costprice_flag == 'table':
                    profit = profitability * common_price / 100
                elif costprice_flag == 'enter':
                    profit = profitability * enter_price / 100
                profit_obj.profitability = profitability
                profit_obj.profit = profit
                profit_obj.save()
                # print('common_price', common_price, 'price', price, mp_product)
                if MarketplaceProductPriceWithProfitability.objects.filter(
                        mp_product=product).exists():
                    mp_product_price = MarketplaceProductPriceWithProfitability.objects.get(
                        mp_product=product)
                    # Обновляем существующий объект
                    mp_product_price.profit_price = enter_price
                    mp_product_price.usual_price = common_price
                    mp_product_price.save()
                else:
                    # Создаем новый объект
                    MarketplaceProductPriceWithProfitability(
                        mp_product=product,
                        profit_price=enter_price,
                        usual_price=common_price
                    ).save()
    if products_to_update:
        MarketplaceProductPriceWithProfitability.objects.bulk_update(products_to_update, ['profit_price', 'usual_price'])
    if products_to_create:
        MarketplaceProductPriceWithProfitability.objects.bulk_create(products_to_create)
    return product_list


def calculate_mp_profitability_with_incoming_price(action_id, product_list: list, costprice_flag='table', order_delivery_type='fbo'):
    """
    Расчет рентабельности товара на маркетплейсе на основе входящей цены в акции.
    
    product_list - список товаров, участвующих в акции

    Возвращает: 
        mp_products_list - список объектов модели MarketplaceProduct

    """
    if order_delivery_type == None:
        order_delivery_type = 'fbo'
    for mp_product in product_list:
        mp_products_list = MarketplaceProduct.objects.filter(id=mp_product.id).select_related(
            'marketproduct_logistic').select_related('marketproduct_comission').select_related('mp_profitability')

        for product in mp_products_list:

            _, overheads, comission_logistic_costs = profitability_part_template(product)

            if ProfitabilityMarketplaceProduct.objects.filter(mp_product=product).exists():
                logistic_cost = comission_logistic_costs[order_delivery_type]['logistic_cost']
                comission = comission_logistic_costs[order_delivery_type]['comission']
                profitability = product.mp_profitability.profitability

                cost_price = 0
                if costprice_flag == 'table':
                    cost_price = product.product.cost_price
                elif costprice_flag == 'enter':
                    if ProductCostPrice.objects.filter(
                            product=product.product).exists():
                        cost_price = ProductCostPrice.objects.get(
                            product=product.product).cost_price
                    else:
                        cost_price = 0
                # Цена товара в акции
                price = MarketplaceProductInAction.objects.get(action__id=action_id, marketplace_product=product).product_price
                profit_obj = ProfitabilityMarketplaceProduct.objects.get(mp_product=product)
                
                profit = round((price - float(cost_price) -
                                logistic_cost - (comission * price / 100) - (overheads * price)), 2)
                
                profitability = round(((profit / price) * 100), 2)

                
                profit_obj.profitability = profitability
                profit_obj.profit = profit
                profit_obj.save()
        
    return product_list

def changer_price_in_moy_sklad(user_id,
                               product_obj, 
                               mp_product_obj, 
                               productprice_obj, 
                               new_price):
    """Вспомогательная функция для изменения цены на Моем Складе"""
    product_type = mp_product_obj.product.product_type
    platform_id = mp_product_obj.platform.id
    account_obj = Account.objects.get(id=mp_product_obj.account.id)
    moy_sklad_account = Account.objects.get(
        user=User.objects.get(id=user_id),
        platform=Platform.objects.get(
            platform_type=MarketplaceChoices.MOY_SKLAD)
    )
    moy_sklad_token = moy_sklad_account.authorization_fields['token']
    if platform_id == 1:
        productprice_obj.wb_price = new_price
        productprice_obj.save()
    if platform_id == 2:
        productprice_obj.yandex_price = new_price
        productprice_obj.save()
    if platform_id == 4:
        ozonproductprice_obj = ProductOzonPrice.objects.get(
            product=product_obj, account=account_obj)
        ozonproductprice_obj.ozon_price = new_price
        ozonproductprice_obj.save()
    account_name = account_obj.name
    if product_obj.moy_sklad_product_number:
        new_price = new_price * 100
        change_product_price(moy_sklad_token, platform_id, account_name,
                             new_price, product_obj.moy_sklad_product_number, product_type)
        mp_product_obj.change_price_flag = True
        mp_product_obj.save()
    else:
        message = f"У продукта {product_obj.name} не могу обновить цену на {int(platform_id)} {account_name}. В БД не нашел его ID с Мой склад"
        # for chat_id in ADMINS_CHATID_LIST:
        #     bot.send_message(chat_id=chat_id, text=message[:4000])

def update_price_info_from_user_request(data_dict: dict):
    """
    Обновляет цены на Мой склад и в БД, если пользователь отправил запрос
    {
        'user_id': user_id,
        'quarantine_percent': quarantine_percent,
        'quarantine': true,
        'products_data': [
            {
                'marketplaceproduct_id': marketplaceproduct_id,
                'new_price': new_price
            }
        ]
    }
    """
    user_id = data_dict.get('user_id', '')
    products_data = data_dict.get('products_data', '')
    quarantine_percent = data_dict.get('quarantine_percent', 20)
    quarantine = data_dict.get('quarantine', 'false')

    for data in products_data:
        marketplaceproduct_id = data.get('marketplaceproduct_id', '')
        new_price = data.get('new_price', '')
        if new_price:
            mp_product_obj = MarketplaceProduct.objects.get(
                id=marketplaceproduct_id)
            product_obj = mp_product_obj.product
            productprice_obj = ProductForMarketplacePrice.objects.get(
                product=product_obj)
            rrc = productprice_obj.rrc
            different_between_rrc = abs((new_price - rrc) / rrc * 100)
            if quarantine != True:
                if quarantine_percent >= different_between_rrc:
                    changer_price_in_moy_sklad(user_id,
                               product_obj, 
                               mp_product_obj, 
                               productprice_obj, 
                               new_price)
            else:
                changer_price_in_moy_sklad(user_id,
                               product_obj, 
                               mp_product_obj, 
                               productprice_obj, 
                               new_price)


def changer_profitability_calculate(product):
    """
    Вспомогательная функция для подсчета рентабельности.
    Применяется в сигналах изменения различных моделей

    Входящие данные:
    product - объект модели MarketplaceProduct
    """
    account_obj = product.account
    overhead_data = StoreOverhead.objects.filter(account=account_obj).aggregate(
                overhead_sum=Sum('overhead'))
    try:
        overheads = overhead_data['overhead_sum'] / 100
    except:
        overheads = 0.2
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
        except ProfitabilityMarketplaceProduct.DoesNotExist:
            pass
        profit = round((price - float(product_cost_price) -
                        logistic_cost - (comission * price / 100) - (overheads * price)), 2)
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
    account_obj = product.account
    overhead_data = StoreOverhead.objects.filter(account=account_obj).aggregate(
                overhead_sum=Sum('overhead'))
    try:
        overheads = overhead_data['overhead_sum'] / 100
    except:
        overheads = 0.2
    if product.platform.name == 'OZON':
        comission = product.marketproduct_comission.fbs_commission
        logistic_cost = product.marketproduct_logistic.cost_logistic_fbs
    else:
        comission = product.marketproduct_comission.fbs_commission
        logistic_cost = product.marketproduct_logistic.cost_logistic
    if ProfitabilityMarketplaceProduct.objects.filter(mp_product=product).exists():
        profitability = product.mp_profitability.profitability
        common_product_cost_price = product.product.cost_price/100
        if ProductCostPrice.objects.filter(
                product=product.product).exists():
            profit_product_cost_price = ProductCostPrice.objects.get(
                product=product.product).cost_price
        else:
            profit_product_cost_price = 0
        # Цена на основе обычной себестоимости (на основе себестоимости комплектов)
        common_price = round(((common_product_cost_price/100 +  logistic_cost
                               ) / (1 - profitability/100 - comission/100 - overheads)), 2)
        # Цена на основе себестоимости по оприходованию
        enter_price = round(((profit_product_cost_price + logistic_cost
                              ) / (1 - profitability/100 - comission/100 - overheads)), 2)
        search_params = {'mp_product': product}

        values_for_update = {
            "profit_price": enter_price,
            "usual_price": common_price
        }
        MarketplaceProductPriceWithProfitability.objects.update_or_create(
            defaults=values_for_update, **search_params)


def calculate_quarantine_mp_products(quarantine_percent, queryset):
    """
    Фильтрует карантинные товары
    """
    percent = 20
    if quarantine_percent:
        percent = int(quarantine_percent)
    percent = percent / 100
    great = 1 + percent
    less = 1 - percent
    queryset = queryset.annotate(
        wb_price=F('product__price_product__wb_price'),
        yandex_price=F('product__price_product__yandex_price'),
        rrc=F('product__price_product__rrc')
    )
    if queryset:
        platform_id = queryset.first().platform.id
        if platform_id == 1:
            queryset = queryset.filter(
                Q(wb_price__gt=F('rrc') * great) | Q( wb_price__lt=F('rrc') * less)
            )
        elif platform_id == 2:
            queryset = queryset.filter(
                Q(yandex_price__gt=F('rrc') * great) | Q(yandex_price__lt=F('rrc') * less)
            )
        elif platform_id == 4:
            queryset = queryset.filter(
                Q(product__price_product__rrc__gt=F('product__ozon_price_product__ozon_price') * great) | Q(product__price_product__rrc__lt=F('product__ozon_price_product__ozon_price')* less)
            )
        return queryset
    else:
        return []