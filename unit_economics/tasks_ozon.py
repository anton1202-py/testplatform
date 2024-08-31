import requests
from django.db import transaction
from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from analyticalplatform.settings import TOKEN_WB, TOKEN_MY_SKLAD, TOKEN_OZON, OZON_ID
from api_requests.moy_sklad import moy_sklad_assortment
from api_requests.ozon_requests import ozon_article_info_from_api, ozon_article_list_from_api, ozon_products_comission_info_from_api, ozon_products_info_from_api
from api_requests.wb_requests import wb_article_data_from_api, wb_comissions
from core.enums import MarketplaceChoices
from core.models import Account, Platform, User
from unit_economics.integrations import add_marketplace_product_to_db
from unit_economics.models import MarketplaceCommission, MarketplaceLogistic, ProductPrice
from unit_economics.serializers import ProductPriceSerializer
import logging

logger = logging.getLogger(__name__)


def ozon_price_articles(TOKEN_OZON, OZON_ID):
    """
    Возвращает словарь типа {product_id: price_after_discount}
    """
    data_list = ozon_products_comission_info_from_api(TOKEN_OZON, OZON_ID)
    price_dict = {}
    if data_list:
        for data in data_list:
            price_dict[data['product_id']] = data['price']['price']
    return price_dict



def ozon_comission_logistic_add_data_to_db():
    """
    Записывает комиссии и затрат на логистику OZON в базу данных
    """
    data_list = ozon_products_comission_info_from_api(TOKEN_OZON, OZON_ID)

    users = User.objects.all()
    if data_list:
        for user in users:
            account, created = Account.objects.get_or_create(
                    user=user,
                    platform=Platform.objects.get(platform_type=MarketplaceChoices.OZON),
                )
            goods_categories = ProductPrice.objects.filter(account=account, platform=Platform.objects.get(platform_type=MarketplaceChoices.OZON))
            for data in data_list:
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

    

def ozon_products_data_to_db():
    """Записывает данные о продуктах OZON в базу данных"""
    users = User.objects.all()
    for user in users:
        account_sklad, created = Account.objects.get_or_create(
                user=user,
                platform=Platform.objects.get(platform_type=MarketplaceChoices.MOY_SKLAD),
            )
        accounts_ozon = Account.objects.filter(
                user=user,
                platform=Platform.objects.get(platform_type=MarketplaceChoices.OZON)
            )
        for account in accounts_ozon:
            ozon_token = account.authorization_fields['token']
            ozon_client_id = account.authorization_fields['client_id']
            main_data = ozon_products_info_from_api(ozon_token, ozon_client_id)
            price_data = ozon_price_articles(ozon_token, ozon_client_id)
            for data in main_data:
                platform = Platform.objects.get(platform_type=MarketplaceChoices.OZON)
                name = data['name']
                brand = ''
                sku = data['id']
                vendor = data['offer_id']
                barcode = data['barcode']
                price = price_data.get(data['id'], 0)
                category_number = data['description_category_id']
                category_name = ''
                width = data['width']/10
                height = data['height']/10
                length = data['depth']/10
                weight=data['weight']/1000

                add_marketplace_product_to_db(
                    account_sklad, barcode, 
                    account, platform, name, 
                    brand, sku, vendor, category_number, 
                    category_name, price, width, 
                    height, length, weight)
