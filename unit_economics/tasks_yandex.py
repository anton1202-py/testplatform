import math
import requests
from django.db import transaction
from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from analyticalplatform.settings import TOKEN_WB, TOKEN_MY_SKLAD, TOKEN_OZON, OZON_ID, TOKEN_YM
from api_requests.moy_sklad import moy_sklad_assortment
from api_requests.ozon_requests import ozon_article_info_from_api, ozon_article_list_from_api, ozon_products_comission_info_from_api, ozon_products_info_from_api
from api_requests.wb_requests import wb_article_data_from_api, wb_comissions
from api_requests.yandex_requests import yandex_campaigns_data, yandex_campaigns_from_business, yandex_comission_calculate
from core.enums import MarketplaceChoices
from core.models import Account, Platform, User
from unit_economics.integrations import add_marketplace_product_to_db
from unit_economics.models import MarketplaceCommission, MarketplaceLogistic, ProductPrice
from unit_economics.serializers import ProductPriceSerializer
import logging

logger = logging.getLogger(__name__)


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


def yandex_add_campaigns_data_to_db():
    """Записывает данные артикулов в базу данных
    
    Входящие переменные:
        TOKEN_YM - Bearer токен с яндекс маркета
    """
    users = User.objects.all()
    for user in users:
        account_sklad, created = Account.objects.get_or_create(
                user=user,
                platform=Platform.objects.get(platform_type=MarketplaceChoices.MOY_SKLAD),
            )
        accounts_ya = Account.objects.filter(
                user=user,
                platform=Platform.objects.get(platform_type=MarketplaceChoices.YANDEX_MARKET)
            )
        for account in accounts_ya:
            token_ya = account.authorization_fields['token']
            business_list = yandex_business_list(token_ya)
            if business_list:
                for business_id in business_list:
                    articles_data = yandex_campaigns_from_business(token_ya, business_id)
                    for data in articles_data:
                        if 'marketSku' in data['mapping']:
                            platform = Platform.objects.get(platform_type=MarketplaceChoices.YANDEX_MARKET)
                            market_data = data.get('mapping', '')
                            product_data = data.get('offer', '')
                            barcode = product_data.get('barcodes', 0)
                            if barcode:
                                barcode = barcode[0]
                                name = market_data.get('marketSkuName', '')
                                brand = product_data.get('vendor', '')
                                sku = market_data.get('marketSku', 0)
                                vendor = product_data.get('offerId', '')

                                price = product_data['basicPrice']['value']
                                category_number = market_data.get('marketCategoryId', 0)
                                category_name = market_data.get('marketCategoryName', '')                            
                            
                                if 'weightDimensions' in product_data:
                                    # print(product_data['weightDimensions'])
                                    width = product_data['weightDimensions']['width']
                                    height = product_data['weightDimensions']['height']
                                    length = product_data['weightDimensions']['length']
                                    if 'weight' in product_data['weightDimensions']:
                                        weight = product_data['weightDimensions']['weight']
                                add_marketplace_product_to_db(
                                    account_sklad, barcode, 
                                    account, platform, name, 
                                    brand, sku, vendor, category_number, 
                                    category_name, price, width, 
                                    height, length, weight
                                )
                

def yandex_comission_logistic_add_data_to_db():
    """
    Записывает комиссии и затраты на логистику YANDEX MARKET в базу данных
    """

    users = User.objects.all()

    for user in users:
        account, created = Account.objects.get_or_create(
                user=user,
                platform=Platform.objects.get(platform_type=MarketplaceChoices.OZON),
            )
        data_list = ProductPrice.objects.filter(
            account=account, 
            platform=Platform.objects.get(platform_type=MarketplaceChoices.YANDEX_MARKET)
        )

        amount_articles = math.ceil(len(data_list)/150)
        for i in range(amount_articles):
            start_point = i*150
            finish_point = (i+1)*150
            request_article_list = data_list[
                start_point:finish_point]
            request_data = []
            for data in request_article_list:
                if data.weight:
                    inner_request_dict = {   
                        "categoryId": data.category_number,
                        "price": data.price,
                        "length": data.length,
                        "width": data.width,
                        "height": data.height,
                        "weight": data.weight,
                        "quantity": 1
                    }
                    request_data.append(inner_request_dict)
            comission_data = yandex_comission_calculate(TOKEN_YM, request_data)

            for comission in comission_data:
                article_data = comission['offer']
                product_obj = ProductPrice.objects.get(
                    account=account, 
                    platform=Platform.objects.get(platform_type=MarketplaceChoices.YANDEX_MARKET),
                    category_number=comission['offer']['categoryId'],
                    price=comission['offer']['price'],
                    length=comission['offer']['length'],
                    width=comission['offer']['width'],
                    height=comission['offer']['height'],
                    weight=comission['offer']['weight']
                )
                product_comission = 0
                for amount in comission['tariffs']:
                    if amount['type'] == 'FEE':
                        product_comission = amount['amount']
                product_comission =  amount

        for data in data_list:
            request_data
            product_obj = ProductPrice.objects.get(
                account=account, 
                platform=Platform.objects.get(platform_type=MarketplaceChoices.OZON),
                sku=data['product_id'])
            fbs_commission=data['commissions']['sales_percent_fbs']
            fbo_commission=data['commissions']['sales_percent_fbo']
            if MarketplaceCommission.objects.filter(product=product_obj).exists():
                MarketplaceCommission.objects.filter(product=product_obj).update(
                    fbs_commission=fbs_commission,
                    fbo_commission=fbo_commission
                )
            else:
                MarketplaceCommission(
                    product=product_obj,
                    fbs_commission=fbs_commission,
                    fbo_commission=fbo_commission
                ).save()
            cost_logistic_fbo = data['commissions']['fbo_deliv_to_customer_amount'] + data['commissions']['fbo_fulfillment_amount'] + data['commissions']['fbo_direct_flow_trans_min_amount']
            cost_logistic_fbs = data['commissions']['fbs_deliv_to_customer_amount'] + data['commissions']['fbs_direct_flow_trans_min_amount']
            if MarketplaceLogistic.objects.filter(product=product_obj).exists():
                MarketplaceLogistic.objects.filter(product=product_obj).update(
                    cost_logistic_fbo=cost_logistic_fbo,
                    cost_logistic_fbs=cost_logistic_fbs
                )
            else:
                MarketplaceLogistic(
                    product=product_obj,
                    cost_logistic_fbo=cost_logistic_fbo,
                    cost_logistic_fbs=cost_logistic_fbs
                ).save()