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
from unit_economics.models import MarketplaceCommission, MarketplaceLogistic, MarketplaceProduct, ProductPrice
from unit_economics.serializers import ProductPriceSerializer
import logging

logger = logging.getLogger(__name__)



    

def add_marketplace_product_to_db(
        account_sklad, barcode, 
        account, platform, name, 
        brand, sku, vendor, category_number, 
        category_name, price, width, 
        height, length, weight):
    """
    Записывает данные о продуктах маркетплейсов после сопоставления с основными продуктами в базу данных
    """
    
    product_data = ProductPrice.objects.filter(account=account_sklad)
    objects_for_create = []
    for product in product_data:
        bc_list = product.barcode
        if str(barcode) in bc_list:
            if not MarketplaceProduct.objects.filter(account=account, platform=platform, product=product):
                product_obj = MarketplaceProduct(
                    account=account,
                    platform=platform,
                    product=product,
                    name=name,
                    brand=brand,
                    sku=sku,
                    vendor=vendor,
                    barcode=barcode,
                    category_number=category_number,
                    category_name=category_name,
                    price=price,
                    width=width,
                    height=height,
                    length=length,
                    weight=weight
                )
                objects_for_create.append(product_obj)
            else:
                MarketplaceProduct.objects.filter(account=account, platform=platform, product=product).update(
                    name=name,
                    brand=brand,
                    vendor=vendor,
                    barcode=barcode,
                    price=price,
                    category_number=category_number,
                    category_name=category_name,
                    width=width,
                    height=height,
                    length=length,
                    weight=weight
                )
        continue
    MarketplaceProduct.objects.bulk_create(objects_for_create)
