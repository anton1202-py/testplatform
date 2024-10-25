import logging
import math
from datetime import datetime

from api_requests.yandex_requests import (yandex_actions_list,
                                          yandex_actions_product_price_info,
                                          yandex_campaigns_data,
                                          yandex_campaigns_from_business,
                                          yandex_comission_calculate)
from core.enums import MarketplaceChoices
from core.models import Account, Platform, User
from unit_economics.integrations import (add_marketplace_comission_to_db,
                                         add_marketplace_logistic_to_db,
                                         add_marketplace_product_to_db, sender_error_to_tg)
from unit_economics.models import (MarketplaceAction, MarketplaceProduct,
                                   MarketplaceProductInAction,
                                   ProductForMarketplacePrice)


logger = logging.getLogger(__name__)


@sender_error_to_tg
def yandex_business_list(TOKEN_YM):
    """Возвращает список business_id с аккаунта продавцы"""
    main_data = yandex_campaigns_data(TOKEN_YM)
    business_list = []
    if main_data:
        for data in main_data:
            business_id = data['business']['id']
            if business_id not in business_list:
                business_list.append(data['business']['id'])
    return business_list


@sender_error_to_tg
def yandex_add_products_data_to_db():
    """Записывает данные артикулов в базу данных

    Входящие переменные:
        TOKEN_YM - Bearer токен с яндекс маркета
    """
    users = User.objects.all()
    for user in users:
        if Account.objects.filter(
            user=user,
            platform=Platform.objects.get(
                platform_type=MarketplaceChoices.MOY_SKLAD)
        ).exists():
            account_sklad = Account.objects.get(
                user=user,
                platform=Platform.objects.get(
                    platform_type=MarketplaceChoices.MOY_SKLAD)
            )
            accounts_ya = Account.objects.filter(
                user=user,
                platform=Platform.objects.get(
                    platform_type=MarketplaceChoices.YANDEX_MARKET)
            )
            for account in accounts_ya:
                token_ya = account.authorization_fields['token']
                business_list = yandex_business_list(token_ya)
                if business_list:
                    main_data = []
                    for business_id in business_list:
                        articles_data = yandex_campaigns_from_business(
                            token_ya, business_id)
                        for data in articles_data:
                            main_data.append(data)
                    existing_products = MarketplaceProduct.objects.filter(account=account)
                    api_skus = {data['mapping']['marketSku'] for data in main_data if
                                    'marketSku' in data['mapping']}
                    for product in existing_products:
                        if int(product.sku) in api_skus:
                            product.is_active = True
                            api_skus.remove(int(product.sku))
                        else:
                            product.is_active = False
                        product.save()

                    for data in main_data:
                        if 'marketSku' in data['mapping']:
                            platform = Platform.objects.get(
                                platform_type=MarketplaceChoices.YANDEX_MARKET)
                            market_data = data.get('mapping', '')
                            product_data = data.get('offer', '')
                            barcode = product_data.get('barcodes', 0)                                
                            if barcode:
                                barcode = barcode[0]
                                name = market_data.get('marketSkuName', '')
                                sku = market_data.get('marketSku', 0)
                                seller_article = product_data.get(
                                    'offerId', '')
                                category_number = market_data.get(
                                    'marketCategoryId', 0)
                                category_name = market_data.get(
                                    'marketCategoryName', '')
                                if 'weightDimensions' in product_data:
                                    width = product_data['weightDimensions']['width']
                                    height = product_data['weightDimensions']['height']
                                    length = product_data['weightDimensions']['length']
                                    if width == 0:
                                        width = 20
                                    if height == 0:
                                        height = 20
                                    if length == 0:
                                        length = 20
                                    if 'weight' in product_data['weightDimensions']:
                                        weight = product_data['weightDimensions']['weight']
                                add_marketplace_product_to_db(
                                    account_sklad, barcode,
                                    account, platform, name,
                                    sku, seller_article, category_number,
                                    category_name, width,
                                    height, length, weight
                                )


@sender_error_to_tg
def yandex_comission_logistic_add_data_to_db():
    """
    Записывает комиссии и затраты на логистику YANDEX MARKET в базу данных
    """
    selling_program_list = ['EXPRESS', 'FBS', 'FBY']
    users = User.objects.all()
    for user in users:
        accounts_ya = Account.objects.filter(
            user=user,
            platform=Platform.objects.get(
                platform_type=MarketplaceChoices.YANDEX_MARKET)
        )
        for account in accounts_ya:
            token_ya = account.authorization_fields['token']
            data_list = MarketplaceProduct.objects.filter(
                account=account,
                platform=Platform.objects.get(
                    platform_type=MarketplaceChoices.YANDEX_MARKET)
            )
            article_comission = {}
            amount_articles = math.ceil(len(data_list)/150)
            for i in range(amount_articles):
                start_point = i*150
                finish_point = (i+1)*150
                request_article_list = data_list[
                    start_point:finish_point]

                for logistic_type in selling_program_list:
                    request_data = []

                    for data in request_article_list:
                        product_obj = data.product
                        price = ProductForMarketplacePrice.objects.get(
                            product=product_obj).yandex_price
                        if data.weight:
                            inner_request_dict = {
                                "categoryId": data.category.category_number,
                                # float(data.product.ya_price),
                                "price": price,
                                "length": data.length,
                                "width": data.width,
                                "height": data.height,
                                "weight": data.weight,
                                "quantity": 1
                            }
                            request_data.append(inner_request_dict)
                    comission_data = yandex_comission_calculate(
                        token_ya, logistic_type, request_data)
                    for comission in comission_data:
                        article_data = comission['offer']
                        product_objects = MarketplaceProduct.objects.filter(
                            account=account,
                            platform=Platform.objects.get(
                                platform_type=MarketplaceChoices.YANDEX_MARKET),
                            category__category_number=article_data['categoryId'],
                            # price=article_data['price'],
                            length=article_data['length'],
                            width=article_data['width'],
                            height=article_data['height'],
                            weight=article_data['weight']
                        )
                        for prod_obj in product_objects:
                            price = prod_obj.product.price_product.yandex_price
                            product_comission = 0
                            delivery_to_customer = 0
                            middle_mile = 0
                            sorting = 0

                            for amount in comission['tariffs']:
                                if amount['type'] == 'FEE':
                                    product_comission = amount['amount'] / price * 100
                                elif amount['type'] == 'DELIVERY_TO_CUSTOMER':
                                    delivery_to_customer = amount['amount']
                                elif amount['type'] == 'MIDDLE_MILE':
                                    middle_mile = amount['amount']
                                elif amount['type'] == 'SORTING':
                                    sorting += amount['amount']
                            logistic_cost = (delivery_to_customer + \
                                middle_mile + sorting )
                            # print('logistic_cost', logistic_cost, 'logistic_type', logistic_type, prod_obj)
                            # print('**********************')
                            add_marketplace_logistic_to_db(
                                prod_obj, cost_logistic=logistic_cost, cost_logistic_fbo=None, cost_logistic_fbs=None)

                            if prod_obj not in article_comission:
                                article_comission[prod_obj] = {
                                    logistic_type: product_comission}
                            else:
                                article_comission[prod_obj][logistic_type] = product_comission

            for prod_obj, value in article_comission.items():
                add_marketplace_comission_to_db(
                    prod_obj, fbs_commission=value['FBS'], fbo_commission=value['FBY'], dbs_commission=0, fbs_express_commission=value['EXPRESS'])


@sender_error_to_tg
def yandex_action_data_to_db():
    """
    Записывает данные акций YANDEX в базу данных.
    """
    accounts_ozon = Account.objects.filter(
        platform=Platform.objects.get(
            platform_type=MarketplaceChoices.YANDEX_MARKET)
    )
    for account in accounts_ozon:
        ya_token = account.authorization_fields['token']
        business_list = yandex_business_list(ya_token)
        if business_list:
            for business_id in business_list:
                actions_data = yandex_actions_list(ya_token, business_id)
                for action in actions_data:
                    platform = account.platform
                    action_number = f"{action['id']} {business_id}"
                    action_name = action['name']
                    date_start = datetime.fromisoformat(
                        action['period']['dateTimeFrom'])
                    date_finish = datetime.fromisoformat(
                        action['period']['dateTimeTo'])
                    search_params = {'platform': platform,
                                     'account': account, 'action_number': action_number}
                    values_for_update = {
                        "action_name": action_name,
                        "date_start": date_start,
                        "date_finish": date_finish
                    }
                    MarketplaceAction.objects.update_or_create(
                        defaults=values_for_update, **search_params)


def yandex_action_article_price_to_db(account, actions_data, platform):
    """
    Записывает возможные цены артикулов YANDEX из акции
    """
    for data in actions_data:
        ya_token = account.authorization_fields['token']
        common_data = data.action_number
        parts = common_data.split()
        action_id = parts[0]
        business_id = parts[1]
        action_data = yandex_actions_product_price_info(
            ya_token, business_id, action_id)
        if action_data:
            for action_ya in action_data:
                nom_id = action_ya['offerId']
                if MarketplaceProduct.objects.filter(
                        account=account, seller_article=nom_id).exists():
                        for marketplace_product in MarketplaceProduct.objects.filter(
                            account=account, seller_article=nom_id):
                            action = data
                            if 'discountParams' in action_ya['params']:
                                product_price = action_ya['params']['discountParams']['maxPromoPrice']
                            else:
                                product_price = action_ya['params']['promocodeParams']['maxPrice']
                            if action_ya['status'] == 'NOT_PARTICIPATING':
                                status = False
                            else:
                                status = True
                            search_params = {'action': action,
                                             'marketplace_product': marketplace_product}
                            values_for_update = {
                                "product_price": product_price,
                                "status": status
                            }
                            MarketplaceProductInAction.objects.update_or_create(
                                defaults=values_for_update, **search_params)
