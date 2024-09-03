import datetime
import json
import time
from datetime import datetime
import requests
from django.db import transaction
from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from analyticalplatform.settings import TOKEN_WB, TOKEN_MY_SKLAD, TOKEN_OZON, OZON_ID, TOKEN_YM
from core.enums import MarketplaceChoices
from core.models import Account, Platform
from unit_economics.models import ProductPrice
from unit_economics.serializers import ProductPriceSerializer
import logging

logger = logging.getLogger(__name__)


def yandex_campaigns_data(TOKEN_YM):
    """Определяет магазины у пользователя"""
    api_url = f"https://api.partner.market.yandex.ru/campaigns"
    headers = {
        'Authorization': f'Bearer {TOKEN_YM}'
    }
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        campaigns_list = response.json().get('campaigns', [])
        return campaigns_list


def yandex_campaigns_from_business(TOKEN_YM, business_id, limit=100, page_token='', data_list=None):
    """Возвращает список кампаний от входящего business_id
    
    Входящие переменные:
        TOKEN_YM - Bearer токен с яндекс маркета
        business_id - кабинет, с которого нужно вытянуть товары
    """
    if not data_list:
        data_list = []
    api_url = f"https://api.partner.market.yandex.ru/businesses/{business_id}/offer-mappings?limit={limit}&page_token={page_token}"
    headers = {
        'Authorization': f'Bearer {TOKEN_YM}'
    }
    payload = {}
    response = requests.request("POST", api_url, headers=headers, data=payload)
    if response.status_code == 200:
        all_data = json.loads(response.text)["result"]['offerMappings']
        for data in all_data:
            data_list.append(data)
        if len(all_data) == limit:
            page_token = json.loads(response.text)["result"]['paging']['nextPageToken']
            return yandex_campaigns_from_business(TOKEN_YM, business_id, limit, page_token, data_list)
        else:
            return data_list


def yandex_comission_calculate(TOKEN_YM: str, logistic_type: str, offers_list: list) -> list:
    """
    Рассчитывает стоимость услуг Маркета для товаров с заданными параметрами. 
    Порядок товаров в запросе и ответе сохраняется, чтобы определить, для какого товара рассчитана стоимость услуги.
    Обратите внимание: калькулятор осуществляет примерные расчеты. 
    Финальная стоимость для каждого заказа зависит от предоставленных услуг.
    В запросе можно указать либо параметр campaignId, либо sellingProgram. 
    Совместное использование параметров приведет к ошибке.
    """

    api_url = f"https://api.partner.market.yandex.ru/tariffs/calculate"
    headers = {
        'Authorization': f'Bearer {TOKEN_YM}'
    }
    payload = json.dumps({
        "parameters": {
            "sellingProgram": logistic_type,
            "frequency": "DAILY"
        },
        "offers": offers_list
    })
    response = requests.request("POST", api_url, headers=headers, data=payload)
    if response.status_code != 200:
        print('response.status_code', response.text)
    if response.status_code == 200:
        main_data = response.json().get('result', [])
        if main_data:
            comission_list = main_data.get('offers')
            return comission_list