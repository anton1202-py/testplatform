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


def moy_sklad_assortment(TOKEN_MY_SKLAD, offset=0, iter_numb=0, products_data_list=[]):
    """
    Достает список всех товаров с учетной записи в моем складе

    Входящие переменные:
        TOKEN_MY_SKLAD - токен учетной записи
        offset=0 - Начальная позиция
        iter_numb=0 - Счетчик вызовов метода
        products_data_list=[] - список с данными всех продуктов
    """
    limit = 100  # Количество товаров за один запрос
    api_url = f"https://api.moysklad.ru/api/remap/1.2/entity/assortment?limit={limit}&offset={offset}&filter=archived=false;type=product;type=bundle"
    headers = {
        'Authorization': f'Bearer {TOKEN_MY_SKLAD}',
        'Accept-Encoding': 'gzip',
        'Content-Type': 'application/json'
    }
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        products = data.get('rows', [])
        for product in products:
            products_data_list.append(product)
        if len(products) == limit:
            iter_numb += 1
            offset = limit*iter_numb
            return moy_sklad_assortment(TOKEN_MY_SKLAD, offset, iter_numb, products_data_list)
        else:
            return products_data_list
    else:
        message = f'Ошибка при вызовае метода https://api.moysklad.ru/api/remap/1.2/entity/assortment?limit=limit&offset=offset&filter=archived=false;type=product;type=bundle: {response.status_code}. {response.text}'
        print(message)
