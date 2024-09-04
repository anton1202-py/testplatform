import logging
import math

from api_requests.yandex_requests import (yandex_campaigns_data,
                                          yandex_campaigns_from_business,
                                          yandex_comission_calculate)
from core.enums import MarketplaceChoices
from core.models import Account, Platform, User
from unit_economics.integrations import (add_marketplace_comission_to_db,
                                         add_marketplace_logistic_to_db,
                                         add_marketplace_product_to_db,
                                         sender_error_to_tg)
from unit_economics.models import MarketplaceProduct

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
                for business_id in business_list:
                    articles_data = yandex_campaigns_from_business(
                        token_ya, business_id)
                    for data in articles_data:
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
    selling_program_list = ['FBS', 'FBY', 'DBS', 'EXPRESS']
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
            article_logistic = {}
            amount_articles = math.ceil(len(data_list)/150)
            for i in range(amount_articles):
                start_point = i*150
                finish_point = (i+1)*150
                request_article_list = data_list[
                    start_point:finish_point]

                for logistic_type in selling_program_list:
                    request_data = []

                    for data in request_article_list:
                        if data.weight:
                            inner_request_dict = {
                                "categoryId": data.category.category_number,
                                "price": 2000,  # float(data.product.ya_price),
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
                            product_comission = 0
                            delivary_to_customer = 0
                            middle_mile = 0
                            express_delivery = 0
                            sorting = 0

                            for amount in comission['tariffs']:
                                if amount['type'] == 'FEE':
                                    product_comission = amount['amount']
                                if amount['type'] == 'DELIVERY_TO_CUSTOMER':
                                    delivary_to_customer = amount['amount']
                                if amount['type'] == 'MIDDLE_MILE':
                                    middle_mile = amount['amount']
                                if amount['type'] == 'SORTING':
                                    sorting += amount['amount']
                                if amount['type'] == 'EXPRESS_DELIVERY':
                                    express_delivery = amount['amount']
                            logistic_comission = delivary_to_customer + \
                                middle_mile + express_delivery + sorting
                            add_marketplace_logistic_to_db(
                                prod_obj, cost_logistic=product_comission, cost_logistic_fbo=None, cost_logistic_fbs=None)

                            if prod_obj not in article_logistic:
                                article_logistic[prod_obj] = {
                                    logistic_type: logistic_comission}
                            else:
                                article_logistic[prod_obj][logistic_type] = logistic_comission

            for prod_obj, value in article_logistic.items():
                add_marketplace_comission_to_db(
                    prod_obj, fbs_commission=value['FBS'], fbo_commission=value['FBY'], dbs_commission=0, fbs_express_commission=value['EXPRESS'])
