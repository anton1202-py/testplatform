import json
import time
import requests
from django.db import transaction
from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from analyticalplatform.settings import TOKEN_WB, TOKEN_MY_SKLAD, TOKEN_OZON, OZON_ID
from core.enums import MarketplaceChoices
from core.models import Account, Platform
from unit_economics.models import ProductPrice
from unit_economics.serializers import ProductPriceSerializer
import logging

logger = logging.getLogger(__name__)


def ozon_article_list_from_api(TOKEN_OZON, CLEINTID, limit=1000, last_id='', common_data=[]):
    """
    Получаем список всех артикулов OZON
    
    Входящие данные:
        TOKEN_OZON - API токен польователя
        CLEINTID - номер Client_id кабинета пользователя
        limit - лимит на количество выдаваемых товаров в ответе
        last_id - для работы с пагинацией, если число товаров в ответе равно лимиту
        common_data - список для всех артикулов, включая работающую пагинацию
    """
    
    url = 'https://api-seller.ozon.ru/v2/product/list'
    payload = json.dumps(
        {
          "filter": {
            "offer_id": [],
            "product_id": [],
            "visibility": "ALL"
          },
          "last_id": "",
          "limit": limit
        }
    )
    headers = {
        'Client-Id': CLEINTID,
        'Api-Key': TOKEN_OZON
    }
    response = requests.request(
        "POST", url, headers=headers, data=payload)
    if response.status_code == 200:
        all_data = json.loads(response.text)["result"]['items']
        last_id = json.loads(response.text)["result"]['last_id']
        total = json.loads(response.text)["result"]['total']
        for data in all_data:
            common_data.append(data)
        if total == limit:
            return ozon_article_list_from_api(TOKEN_OZON, CLEINTID, last_id, common_data)
        else:
            return common_data
    else:
        message = f'статус код {response.status_code} у получения списка всех артикулов ozon_article_list_from_api'
        # bot.send_message(chat_id=CHAT_ID_ADMIN, text=message)


def ozon_article_info_from_api(TOKEN_OZON, CLEINTID, product_id):
    """
    Получаем информацию о входящем артикуле OZON
    
    Входящие данные:
        TOKEN_OZON - API токен польователя
        CLEINTID - номер Client_id кабинета пользователя
        product_id - id товара ОЗОН
    """
    
    url = 'https://api-seller.ozon.ru/v2/product/info'
    payload = json.dumps(
        {
            "product_id": product_id,
        }
    )
    headers = {
        'Client-Id': CLEINTID,
        'Api-Key': TOKEN_OZON
    }
    response = requests.request(
        "POST", url, headers=headers, data=payload)
    if response.status_code == 200:
        main_data = json.loads(response.text)["result"]
        return main_data
    else:
        message = f'статус код {response.status_code} у получения информации артикула ozon_article_info_from_api'
        # bot.send_message(chat_id=CHAT_ID_ADMIN, text=message)


def ozon_products_info_from_api(TOKEN_OZON, OZON_ID, limit=1000, last_id='', common_data=[]):
    """
    Получаем список всех артикулов OZON
    
    Входящие данные:
        TOKEN_OZON - API токен польователя
        OZON_ID - номер Client_id кабинета пользователя
        limit - лимит на количество выдаваемых товаров в ответе
        last_id - для работы с пагинацией, если число товаров в ответе равно лимиту
        common_data - список для всех артикулов, включая работающую пагинацию
    """
    
    url = 'https://api-seller.ozon.ru/v3/products/info/attributes'
    payload = json.dumps(
        {
            "filter": {
              "product_id": [],
              "visibility": "ALL"
            },
            "limit": limit,
            "last_id": last_id,
            "sort_dir": "ASC"
        }
    )
    headers = {
        'Client-Id': OZON_ID,
        'Api-Key': TOKEN_OZON
    }
    response = requests.request(
        "POST", url, headers=headers, data=payload)
    if response.status_code == 200:
        all_data = json.loads(response.text)["result"]
        total = json.loads(response.text)['total']
        last_id = json.loads(response.text)['last_id']
        
        for data in all_data:
            common_data.append(data)
        if total == limit:
            return ozon_products_info_from_api(TOKEN_OZON, OZON_ID, last_id, common_data)
        else:
            return common_data
    else:
        message = f'статус код {response.status_code} у получения списка всех артикулов ozon_products_info_from_api'
        # bot.send_message(chat_id=CHAT_ID_ADMIN, text=message)



def ozon_products_comission_info_from_api(TOKEN_OZON, OZON_ID, limit=1000, last_id='', common_data=[]):
    """
    Получаем список всех артикулов OZON с информацией о комиссиях
    
    Входящие данные:
        TOKEN_OZON - API токен польователя
        OZON_ID - номер Client_id кабинета пользователя
        limit - лимит на количество выдаваемых товаров в ответе
        last_id - для работы с пагинацией, если число товаров в ответе равно лимиту
        common_data - список для всех артикулов, включая работающую пагинацию
    """
    
    url = 'https://api-seller.ozon.ru/v4/product/info/prices'
    payload = json.dumps(
        {
            "filter": {
                "offer_id": [],
                "product_id": [],
                "visibility": "ALL"
            },
            "last_id": last_id,
            "limit": limit
        }
    )
    headers = {
        'Client-Id': OZON_ID,
        'Api-Key': TOKEN_OZON
    }
    response = requests.request(
        "POST", url, headers=headers, data=payload)
    if response.status_code == 200:
        all_data = json.loads(response.text)["result"]['items']
        total = json.loads(response.text)["result"]['total']
        last_id = json.loads(response.text)["result"]['last_id']
        
        for data in all_data:
            common_data.append(data)
        if total == limit:
            return ozon_products_info_from_api(TOKEN_OZON, OZON_ID, last_id, common_data)
        else:
            return common_data
    else:
        message = f'статус код {response.status_code} у получения списка всех артикулов ozon_products_info_from_api'
        # bot.send_message(chat_id=CHAT_ID_ADMIN, text=message)