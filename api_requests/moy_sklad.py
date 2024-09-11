import json
import logging

import requests
from django.core.files.base import ContentFile
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
    print(response.status_code)
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
        message = f'Ошибка при вызове метода {api_url}: {response.status_code}. {response.text}'
        print(message)


def moy_sklad_enter(TOKEN_MY_SKLAD, offset=0, iter_numb=0, products_data_list=[]):
    """
    Достает список оприходований товаров

    Входящие переменные:
        TOKEN_MY_SKLAD - токен учетной записи
        offset=0 - Начальная позиция
        iter_numb=0 - Счетчик вызовов метода
        products_data_list=[] - список с данными всех продуктов
    """
    limit = 1000  # Количество товаров за один запрос
    api_url = f"https://api.moysklad.ru/api/remap/1.2/entity/enter?limit={limit}&offset={offset}"
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
        message = f'Ошибка при вызове метода {api_url}: {response.status_code}. {response.text}'
        print(message)


def moy_sklad_positions_enter(TOKEN_MY_SKLAD, enter_id):
    """
    Достает товары из оприходования по id оприходования

    Входящие переменные:
        TOKEN_MY_SKLAD - токен учетной записи
        enter_id - id оприходования
    """

    api_url = f"https://api.moysklad.ru/api/remap/1.2/entity/enter/{enter_id}/positions"
    headers = {
        'Authorization': f'Bearer {TOKEN_MY_SKLAD}',
        'Accept-Encoding': 'gzip',
        'Content-Type': 'application/json'
    }
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        products = data.get('rows', [])
        return products
    else:
        message = f'Ошибка при вызове метода {api_url}: {response.status_code}. {response.text}'
        print(message)


def get_assortiment_info(TOKEN_MY_SKLAD, api_url):
    """
    Получаем информацию об ассортименте

    Входящие переменные:
        TOKEN_MY_SKLAD - токен учетной записи
        api_url - id ссылка для обращения
    """
    api_url = f'{api_url}'
    headers = {
        'Authorization': f'Bearer {TOKEN_MY_SKLAD}',
        'Accept-Encoding': 'gzip',
        'Content-Type': 'application/json'
    }
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        message = f'Ошибка при вызове метода {api_url}: {response.status_code}. {response.text}'
        print(message)


def get_stock_info(TOKEN_MY_SKLAD):
    """
    Получаем информацию об остатках продуктов на Мой Склад

    Входящие переменные:
        TOKEN_MY_SKLAD - токен учетной записи
    """
    api_url = 'https://api.moysklad.ru/api/remap/1.2/report/stock/all'
    headers = {
        'Authorization': f'Bearer {TOKEN_MY_SKLAD}',
        'Accept-Encoding': 'gzip',
        'Content-Type': 'application/json'
    }
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        stocks = data.get('rows', [])
        return stocks
    else:
        message = f'Ошибка при вызове метода {api_url}: {response.status_code}. {response.text}'
        print(message)


def change_product_price(TOKEN_MY_SKLAD, platform, account_name, new_price, product_id):
    """
    Изменение цены на продукт на Мой Склад

    Входящие переменные:
        TOKEN_MY_SKLAD - токен учетной записи
    """
    OZON_ACCOUNT_NAME = {
        'Ozon Envium': 'ОЗОН Evium',
        'Озон Комбо': 'ОЗОН Combo',
        'Озон спейс': 'ОЗОН Market Space'
    }
    marketplace_dict = {'WIldberries': 'WB',
                        'Yandex Market': 'Яндекс'
                        }
    api_url = f'https://api.moysklad.ru/api/remap/1.2/entity/product/{product_id}'
    headers = {
        'Authorization': f'Bearer {TOKEN_MY_SKLAD}',
        'Accept-Encoding': 'gzip',
        'Content-Type': 'application/json'
    }
    response = requests.get(url=api_url, headers=headers)
    salePrices = response.json()['salePrices']
    print(salePrices)

    for sp in salePrices:
        if platform != 'OZON':
            if sp['priceType']['name'] == f"Цена {marketplace_dict[platform]} после скидки":
                sp['value'] = new_price
        else:
            if sp['priceType']['name'] == f"Цена {OZON_ACCOUNT_NAME[account_name]}":
                sp['value'] = new_price
    body = '{"salePrices":' + str(salePrices) + '}'
    body = body.replace("\'", "\"")
    body = json.loads(body)
    response = requests.put(url=api_url, headers=headers, json=body)


def picture_href_request(token_moy_sklad, api_url):
    """
    Достает ссылку по которой лежит картинка товара

    Входящие переменные:
        token_moy_sklad - токен учетной записи
        api_url - URL со ссылкой
    """
    headers = {
        'Authorization': f'Bearer {token_moy_sklad}',
        'Accept-Encoding': 'gzip',
        'Content-Type': 'application/json'
    }
    response = requests.get(url=api_url, headers=headers)
    link = ''
    if response.status_code == 200:
        data = response.json()
        picture_list = data.get('rows', [])
        for picture in picture_list:
            if 'miniature' in picture:
                link = picture['miniature']['downloadHref']
                break

    return link


def get_picture_from_moy_sklad(token_moy_sklad, api_url):
    """
    Достает картинку продукта из Моего Склада

    Входящие переменные:
        token_moy_sklad - токен учетной записи
        api_url - URL со ссылкой
    """
    headers = {
        'Authorization': f'Bearer {token_moy_sklad}',
        'Accept-Encoding': 'gzip',
        'Content-Type': 'application/json'
    }
    response = requests.get(url=api_url, headers=headers)

    if response.status_code == 200:
        # Создаем объект модели
        # Получаем имя файла из URL

        filename = f'{api_url.split("/")[-1]}.jpg'
        # Сохраняем изображение
        return filename, ContentFile(response.content)
