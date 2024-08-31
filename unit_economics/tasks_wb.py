import requests
from django.db import transaction
from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from analyticalplatform.settings import TOKEN_WB, TOKEN_MY_SKLAD, TOKEN_OZON, OZON_ID
from api_requests.moy_sklad import moy_sklad_assortment
from api_requests.wb_requests import wb_article_data_from_api, wb_comissions, wb_logistic, wb_price_data_from_api
from core.enums import MarketplaceChoices
from core.models import Account, Platform, User
from unit_economics.integrations import add_marketplace_product_to_db
from unit_economics.models import MarketplaceCommission, MarketplaceLogistic, MarketplaceProduct, ProductPrice
from unit_economics.serializers import ProductPriceSerializer
import logging

logger = logging.getLogger(__name__)


def wb_categories_list(TOKEN_WB):
    """Возвращает список категорий товаров текущего пользователя"""
    main_data =  wb_article_data_from_api(TOKEN_WB)
    categories_dict = {}
    for data in main_data:
        if data['subjectID'] not in categories_dict:
            categories_dict[data['subjectID']] = data['subjectName']
    return categories_dict


def wb_comission_add_data_to_db():
    """
    Записывает комиссии ВБ в базу данных

    Входящие переменные:
        TOKEN_WB - токен учетной записи
    """

    users = User.objects.all()
    for user in users:
        
        accounts_wb = Account.objects.filter(
                user=user,
                platform=Platform.objects.get(platform_type=MarketplaceChoices.WILDBERRIES)
            )
        for account in accounts_wb:
            token_wb = account.authorization_fields['token']
            data_list = wb_comissions(token_wb)
            users = User.objects.all()
            if data_list:
                goods_list = MarketplaceProduct.objects.filter(account=account, platform=Platform.objects.get(platform_type=MarketplaceChoices.WILDBERRIES))
                for data in data_list:
                    for good_data in goods_list:
                        if good_data.category_number == data['subjectID']:
                            MarketplaceCommission.objects.update_or_create(
                                marketplace_product=good_data,
                                fbs_commission=data['kgvpMarketplace'],
                                fbo_commission=data['paidStorageKgvp'],
                                dbs_commission=data['kgvpSupplier'],
                                fbs_express_commission=data['kgvpSupplierExpress']
                            )


def wb_logistic_add_to_db():
    """
    Записывает затраты на логистику ВБ в базу данных

    Входящие переменные:
        TOKEN_WB - токен учетной записи
    """
    users = User.objects.all()
    for user in users:
        
        accounts_wb = Account.objects.filter(
                user=user,
                platform=Platform.objects.get(platform_type=MarketplaceChoices.WILDBERRIES)
            )
        for account in accounts_wb:
            token_wb = account.authorization_fields['token']
            data_list = wb_logistic(token_wb)
            box_delivery_base = 0
            if data_list:
                for data in data_list:
                    if data['warehouseName'] == 'Коледино':
                        box_delivery_base = data['boxDeliveryBase']
                        break
            goods_data = MarketplaceProduct.objects.filter(account=account, platform=Platform.objects.get(platform_type=MarketplaceChoices.WILDBERRIES))

            for good in goods_data:
                height = good.height
                width = good.width
                length = good.length
                value = height * width * length /1000
                box_delivery_base = float(str(box_delivery_base).replace(',', '.'))
                comission = box_delivery_base * value

                if MarketplaceLogistic.objects.filter(marketplace_product=good).exists():
                    MarketplaceLogistic.objects.filter(marketplace_product=good).update(
                        cost_price=comission
                    )
                else:
                    MarketplaceLogistic(
                        marketplace_product=good,
                        cost_price=comission
                    ).save()


def wb_article_price_info(TOKEN_WB):
    """
    Возвращает словарь типа {nm_id: price_with_discount}
    """
    main_data = wb_price_data_from_api(TOKEN_WB)

    article_price_info = {}
    if main_data:
        for data in main_data:

            discounted_price = data['sizes'][0]['discountedPrice']
            article_price_info[data['nmID']] = discounted_price
        return article_price_info

    

def wb_products_data_to_db():
    """Записывает данные о продуктах ВБ в базу данных"""
    users = User.objects.all()
    for user in users:
        account_sklad, created = Account.objects.get_or_create(
                user=user,
                platform=Platform.objects.get(platform_type=MarketplaceChoices.MOY_SKLAD),
            )
        accounts_wb = Account.objects.filter(
                user=user,
                platform=Platform.objects.get(platform_type=MarketplaceChoices.WILDBERRIES)
            )
        for account in accounts_wb:
            token_wb = account.authorization_fields['token']
            main_data =  wb_article_data_from_api(token_wb)

            price_data = wb_article_price_info(token_wb)
            for data in main_data:
                platform = Platform.objects.get(platform_type=MarketplaceChoices.WILDBERRIES)
                name = data['title']
                brand = data['brand']
                sku = data['nmID']
                vendor = data['vendorCode']
                barcode = data['sizes'][0]['skus'][0]
                price = price_data[data['nmID']]
                category_number = data['subjectID']
                category_name = data['subjectName']
                width = data['dimensions']['width']
                height = data['dimensions']['height']
                length = data['dimensions']['length']
                weight=0

                add_marketplace_product_to_db(
                    account_sklad, barcode, 
                    account, platform, name, 
                    brand, sku, vendor, category_number, 
                    category_name, price, width, 
                    height, length, weight)
