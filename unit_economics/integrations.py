import logging
import traceback

import telegram
from django.db.models import Count, Q

from analyticalplatform.settings import ADMINS_CHATID_LIST, TELEGRAM_TOKEN
from core.models import Account, User
from unit_economics.models import (MarketplaceAction, MarketplaceCategory,
                                   MarketplaceCommission, MarketplaceLogistic,
                                   MarketplaceProduct,
                                   MarketplaceProductPriceWithProfitability,
                                   ProductCostPrice,
                                   ProductForMarketplacePrice,
                                   ProductOzonPrice, ProductPrice,
                                   ProfitabilityMarketplaceProduct)

logger = logging.getLogger(__name__)
bot = telegram.Bot(token=TELEGRAM_TOKEN)


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
                bot.send_message(chat_id=chat_id, text=message_error[:4000])

    return wrapper


@sender_error_to_tg
def add_marketplace_product_to_db(
        account_sklad, barcode,
        account, platform, name,
        sku, seller_article, category_number,
        category_name, width,
        height, length, weight):
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
            if not MarketplaceProduct.objects.filter(account=account, platform=platform, product=product, sku=sku,):
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
                    weight=weight
                )
                objects_for_create.append(product_obj)
            else:
                MarketplaceProduct.objects.filter(account=account, platform=platform, product=product, sku=sku).update(
                    name=name,
                    seller_article=seller_article,
                    barcode=barcode,
                    category=category_obj,
                    width=width,
                    height=height,
                    length=length,
                    weight=weight
                )
        continue
    MarketplaceProduct.objects.bulk_create(objects_for_create)


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


@sender_error_to_tg
def profitability_calculate(user_id, overheads=0.2):
    """Расчет рентабельности по изменению для всей таблицы"""
    user = User.objects.get(id=user_id)
    mp_products_list = MarketplaceProduct.objects.filter(account__user=user).select_related(
        'marketproduct_logistic').select_related('marketproduct_comission')
    products_to_update = []
    products_to_create = []
    for product in mp_products_list:

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
        elif product.platform.name == 'Яндекс Маркет':
            price = ProductForMarketplacePrice.objects.get(
                product=product.product).yandex_price
            comission = product.marketproduct_comission.fbs_commission
            logistic_cost = product.marketproduct_logistic.cost_logistic
        product_cost_price = product.product.cost_price/100

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
            profitability = round(((profit / price) * 100), 2)

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
    if products_to_update:
        ProfitabilityMarketplaceProduct.objects.bulk_update(
            products_to_update, ['profit', 'profitability'])

    if products_to_create:
        ProfitabilityMarketplaceProduct.objects.bulk_create(products_to_create)

    result = ProfitabilityMarketplaceProduct.objects.aggregate(
        count_above_20=Count('id', filter=Q(profitability__gt=20)),
        count_between_10_and_20=Count('id', filter=Q(
            profitability__lt=20) & Q(profitability__gt=10)),

        count_between_0_and_10=Count('id', filter=Q(
            profitability__gt=0) & Q(profitability__lt=10)),

        count_between_0_and_minus_10=Count('id', filter=Q(
            profitability__lt=0) & Q(profitability__gt=-10)),
        count_between_minus10_and_minus_20=Count('id', filter=Q(
            profitability__gt=-20) & Q(profitability__lt=-10)),
        count_below_minus_20=Count('id', filter=Q(profitability__lt=-20)),
    )
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


def action_article_price_to_db():
    """
    Записывает возможные цены артикулов из акции
    """
    from unit_economics.tasks_ozon import (ozon_action_article_price_to_db,
                                           ozon_action_data_to_db)
    from unit_economics.tasks_wb import (wb_action_article_price_to_db,
                                         wb_action_data_to_db)
    from unit_economics.tasks_yandex import (yandex_action_article_price_to_db,
                                             yandex_action_data_to_db)
    ozon_action_data_to_db()
    wb_action_data_to_db()
    yandex_action_data_to_db()
    accounts = Account.objects.all()
    for account in accounts:
        platform = account.platform
        if platform.name == 'Wildberries':
            wb_token = account.authorization_fields['token']
            actions_data = MarketplaceAction.objects.filter(
                account=account, platform=platform)
            wb_action_article_price_to_db(
                account, actions_data, platform, wb_token)
        if platform.name == 'OZON':
            actions_data = MarketplaceAction.objects.filter(
                account=account, platform=platform)
            ozon_action_article_price_to_db(account, actions_data, platform)
        if platform.name == 'Yandex Market':
            actions_data = MarketplaceAction.objects.filter(
                account=account, platform=platform)
            yandex_action_article_price_to_db(account, actions_data, platform)
