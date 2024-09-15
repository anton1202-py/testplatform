import json
import logging
import time

import requests
from django.db import transaction
from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from analyticalplatform.settings import (OZON_ID, TOKEN_MY_SKLAD, TOKEN_OZON,
                                         TOKEN_WB)
from core.enums import MarketplaceChoices
from core.models import Account, Platform
from unit_economics.models import ProductPrice
from unit_economics.serializers import ProductPriceSerializer

logger = logging.getLogger(__name__)


def ozon_article_list_from_api(TOKEN_OZON, CLEINTID, limit=1000, last_id='', common_data=None):
    """
    Получаем список всех артикулов OZON

    Входящие данные:
        TOKEN_OZON - API токен польователя
        CLEINTID - номер Client_id кабинета пользователя
        limit - лимит на количество выдаваемых товаров в ответе
        last_id - для работы с пагинацией, если число товаров в ответе равно лимиту
        common_data - список для всех артикулов, включая работающую пагинацию
    """
    if not common_data:
        common_data = []
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


def ozon_products_info_from_api(TOKEN_OZON, OZON_ID, limit=1000, last_id='', common_data=None):
    """
    Получаем список всех артикулов OZON

    Входящие данные:
        TOKEN_OZON - API токен польователя
        OZON_ID - номер Client_id кабинета пользователя
        limit - лимит на количество выдаваемых товаров в ответе
        last_id - для работы с пагинацией, если число товаров в ответе равно лимиту
        common_data - список для всех артикулов, включая работающую пагинацию
    """
    if not common_data:
        common_data = []

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


def ozon_product_info_with_sku_data(token_ozon, ozon_id, product_id):
    """
    Получаем артикул OZON по которому нужны данные

    Входящие данные:
        token_ozon - API токен польователя
        ozon_id - номер Client_id кабинета пользователя
        product_id - идентификатор товара на Озоне.
    """
    api_url = 'https://api-seller.ozon.ru/v2/product/info'
    payload = json.dumps(
        {
            "product_id": product_id,
        }
    )
    headers = {
        'Client-Id': ozon_id,
        'Api-Key': token_ozon
    }
    response = requests.request(
        "POST", api_url, headers=headers, data=payload)
    if response.status_code == 200:
        all_data = json.loads(response.text)["result"]
        return all_data
    else:
        message = f'статус код {response.status_code} у {api_url}. {response.text}'


def ozon_products_comission_info_from_api(TOKEN_OZON, OZON_ID, limit=1000, last_id='', common_data=None):
    """
    Получаем список всех артикулов OZON с информацией о комиссиях

    Входящие данные:
        TOKEN_OZON - API токен польователя
        OZON_ID - номер Client_id кабинета пользователя
        limit - лимит на количество выдаваемых товаров в ответе
        last_id - для работы с пагинацией, если число товаров в ответе равно лимиту
        common_data - список для всех артикулов, включая работающую пагинацию
    """
    if not common_data:
        common_data = []
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


def ozon_actions_list(TOKEN_OZON, OZON_ID):
    """
    Получаем список всех акций OZON, в которых можно участвовать

    Входящие данные:
        TOKEN_OZON - API токен польователя
        OZON_ID - номер Client_id кабинета пользователя
    """

    api_url = 'https://api-seller.ozon.ru/v1/actions'

    headers = {
        'Client-Id': OZON_ID,
        'Api-Key': TOKEN_OZON
    }
    response = requests.request(
        "GET", api_url, headers=headers)
    if response.status_code == 200:
        all_data = json.loads(response.text)["result"]
        return all_data
    else:
        message = f'статус код {response.status_code} у {api_url}'
        # bot.send_message(chat_id=CHAT_ID_ADMIN, text=message)


def ozon_actions_product_price_info(TOKEN_OZON, OZON_ID, action_id, limit=1000, offset=0, counter=0, common_data=None):
    """
    Получаем список всех артикулов OZON с информацией о комиссиях

    Входящие данные:
        TOKEN_OZON - API токен польователя
        OZON_ID - номер Client_id кабинета пользователя
        action_id - id акции
        limit - лимит на количество выдаваемых товаров в ответе
        offset - для работы с пагинацией, если число товаров в ответе равно лимиту
        common_data - список для всех артикулов, включая работающую пагинацию
    """
    if not common_data:
        common_data = []
    api_url = 'https://api-seller.ozon.ru/v1/actions/candidates'
    payload = json.dumps(
        {
            "action_id": action_id,
            "limit": limit,
            "offset": offset
        }
    )
    headers = {
        'Client-Id': OZON_ID,
        'Api-Key': TOKEN_OZON
    }
    response = requests.request(
        "POST", api_url, headers=headers, data=payload)
    if response.status_code == 200:
        all_data = json.loads(response.text)["result"]['products']
        total = json.loads(response.text)["result"]['total']
        counter += 1
        offset = limit * counter
        for data in all_data:
            common_data.append(data)
        if total == limit:
            return ozon_actions_product_price_info(TOKEN_OZON, OZON_ID, action_id, limit, offset, counter, common_data)
        else:
            return common_data
    else:
        message = f'статус код {response.status_code} у {api_url}'
        # bot.send_message(chat_id=CHAT_ID_ADMIN, text=message)
