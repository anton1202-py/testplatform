import calendar
import datetime
import json
import logging
import time
from datetime import datetime

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


def wb_article_data_from_api(TOKEN_WB, update_date=None, mn_id=0, common_data=None, counter=0):
    """Получаем данные всех артикулов в ВБ"""
    if not common_data:
        common_data = []
    if update_date:
        cursor = {
            "limit": 100,
            "updatedAt": update_date,
            "nmID": mn_id
        }
    else:
        cursor = {
            "limit": 100,
            "nmID": mn_id
        }
    url = 'https://suppliers-api.wildberries.ru/content/v2/get/cards/list'
    payload = json.dumps(
        {
            "settings": {
                "cursor": cursor,
                "filter": {
                    "withPhoto": -1
                }
            }
        }
    )
    headers = {
        'Authorization': f'{TOKEN_WB}'
    }
    response = requests.request(
        "POST", url, headers=headers, data=payload)
    counter += 1
    if response.status_code == 200:
        all_data = json.loads(response.text)["cards"]
        check_amount = json.loads(response.text)['cursor']
        for data in all_data:
            common_data.append(data)
        if len(json.loads(response.text)["cards"]) == 100:
            return wb_article_data_from_api(TOKEN_WB,
                                            check_amount['updatedAt'], check_amount['nmID'], common_data, counter)
        else:
            return common_data
    elif response.status_code != 200 and counter <= 50:
        return wb_article_data_from_api(TOKEN_WB, update_date, mn_id, common_data, counter)
    else:
        message = f'статус код {response.status_code} у получения инфы всех артикулов api_request.wb_article_data'
        # bot.send_message(chat_id=CHAT_ID_ADMIN, text=message)


def wb_price_data_from_api(TOKEN_WB, limit=1000, offset='', common_data=None, counter=0):
    """Получаем данные с ценой и скидкой всех артикулов в ВБ"""
    if not common_data:
        common_data = []
    url = f'https://discounts-prices-api.wildberries.ru/api/v2/list/goods/filter?limit={limit}&offset={offset}'

    headers = {
        'Authorization': f'{TOKEN_WB}'
    }
    response = requests.request(
        "GET", url, headers=headers)
    counter += 1
    if response.status_code == 200:
        all_data = json.loads(response.text)["data"]
        article_amount = all_data['listGoods']
        for data in article_amount:
            common_data.append(data)
        if len(article_amount) == limit:
            offset = limit * counter
            return wb_price_data_from_api(TOKEN_WB, limit, offset, common_data, counter)
        else:
            return common_data
    elif response.status_code != 200 and counter <= 50:
        return wb_price_data_from_api(TOKEN_WB, limit, offset, common_data, counter)
    else:
        message = f'статус код {response.status_code} у получения инфы всех артикулов wb_price_data_from_api'
        # bot.send_message(chat_id=CHAT_ID_ADMIN, text=message)


def wb_comissions(TOKEN_WB):
    """
    Достает комиссии всех присутствующих категорий

    Входящие переменные:
        TOKEN_WB - токен учетной записи ВБ
    """
    api_url = f"https://common-api.wildberries.ru/api/v1/tariffs/commission"
    headers = {
        'Authorization': f'{TOKEN_WB}'
    }
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        data = response.json().get('report', [])
        return data
    else:
        message = f'Ошибка при вызовае метода https://common-api.wildberries.ru/api/v1/tariffs/commission: {response.status_code}. {response.text}'
        print(message)


def wb_logistic(TOKEN_WB):
    """
    Достает затраты на логистику в зависимости от габаритов

    Входящие переменные:
        TOKEN_WB - токен учетной записи ВБ
    """
    today_date = datetime.today().strftime('%Y-%m-%d')
    print(today_date)
    api_url = f"https://common-api.wildberries.ru/api/v1/tariffs/box?date={today_date}"
    headers = {
        'Authorization': f'{TOKEN_WB}'
    }
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:

        main_data = response.json().get('response', [])
        if main_data:
            data = main_data['data']['warehouseList']
            return data
    else:
        message = f'Ошибка при вызовае метода https://common-api.wildberries.ru/api/v1/tariffs/box?date: {response.status_code}. {response.text}'
        print(message)


def wb_actions_list(TOKEN_WB):
    """
    Достает доступные акции для аккаунта

    Входящие переменные:
        TOKEN_WB - токен учетной записи ВБ
    """
    start_date = datetime.today().strftime('%Y-%m-01')
    now = datetime.now()
    # Находим последний день текущего месяца
    last_day = calendar.monthrange(now.year, now.month)[1]
    # Форматируем результат
    finish_date = datetime(now.year, now.month, last_day).date()

    api_url = f"https://dp-calendar-api.wildberries.ru/api/v1/calendar/promotions?startDateTime={start_date}T00:00:00Z&endDateTime={finish_date}T00:00:00Z&allPromo=False"
    headers = {
        'Authorization': f'{TOKEN_WB}'
    }
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        main_data = response.json()
        if main_data:
            data = main_data['data']['promotions']
            return data
    else:
        message = f'Ошибка при вызовае метода {api_url}: {response.status_code}. {response.text}'
        print(message)


def wb_actions_product_price_info(TOKEN_WB, action_id):
    """
    Достает данные о возможной цене товаров в акции

    Входящие переменные:
        TOKEN_WB - токен учетной записи ВБ
        action_id - номер акции
    """

    api_url = f"https://dp-calendar-api.wildberries.ru/api/v1/calendar/promotions/nomenclatures?promotionID={action_id}&inAction=false"
    headers = {
        'Authorization': f'{TOKEN_WB}'
    }
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        main_data = response.json()
        if main_data:
            data = main_data['data']['nomenclatures']
            return data
    else:
        message = f'Ошибка при вызовае метода {api_url}: {response.status_code}. {response.text}'
        print(message)
        return None
