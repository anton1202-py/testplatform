import requests
from django.db import transaction
from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from analyticalplatform.settings import TOKEN_WB, TOKEN_MY_SKLAD, TOKEN_OZON, OZON_ID
from api_requests.moy_sklad import moy_sklad_assortment
from core.enums import MarketplaceChoices
from core.models import Account, Platform
from unit_economics.models import ProductPrice
from unit_economics.serializers import ProductPriceSerializer
import logging

logger = logging.getLogger(__name__)


def moy_sklad_add_data_to_db(TOKEN_MY_SKLAD, account):
    """
    Записывает данные Мой Склад в базу данных

    Входящие переменные:
        TOKEN_MY_SKLAD - токен учетной записи
        account - объект модели Account
    """
    products_data_list = moy_sklad_assortment(TOKEN_MY_SKLAD)
    product_data = []
    if products_data_list:
        for item in products_data_list:
            # Добавляем продукты и информацию о них в список
            attributes_list = item['attributes']
            brand = ''
            for attribute in attributes_list:
                if attribute['name'] == 'Бренд':
                    brand = attribute['value']
            # Извлечение цен
            sale_prices_list = item.get('salePrices', [])
            wb_price_after_discount = ''
            for price in sale_prices_list:
                if price['priceType']['name'] == 'Цена РРЦ МС':
                    wb_price_after_discount = price['value']


            # Извлечение себестоимости
            if item['meta']['type'] == 'product':
                cost_price = item.get('buyPrice', {}).get('value', 0)  # Используем 0 как дефолтное значение

            elif item['meta']['type'] == 'bundle':
                components_url = item['components']['meta']['href']
                headers = {
                    'Authorization': f'Bearer {TOKEN_MY_SKLAD}',
                    'Accept-Encoding': 'gzip',
                    'Content-Type': 'application/json'
                }

                response = requests.get(components_url, headers=headers)

                if response.status_code == 200:
                    components_data = response.json()
                    total_cost_price = 0
                    list_url_products = []
                    for component in components_data.get('rows', []):
                        product_url = component['assortment']['meta']['href']
                        quantity = component.get('quantity')
                        list_url_products.append((product_url, quantity))

                    for product_url, quantity in list_url_products:
                        response_url = requests.get(product_url, headers=headers)

                        if response_url.status_code == 200:
                            cost_price_data = response_url.json()
                            total_cost_price += cost_price_data.get('buyPrice', {}).get('value', 0) * quantity
                        else:
                            message = f'Ошибка при вызове метода (продукт): {response_url.status_code}. {response_url.text}'
                            print(message)
                            total_cost_price = None
                            break  # Прекращаем суммирование, если есть ошибка

                    cost_price = total_cost_price

                else:
                    message = f'Ошибка при вызове метода (компоненты): {response.status_code}. {response.text}'
                    print(message)
                    cost_price = None
            else:
                cost_price = None

            product_info = {
                'account': account,
                'platform': Platform.objects.get(platform_type=MarketplaceChoices.MOY_SKLAD),
                'sku': item.get('id', ''),
                'name': item.get('name', ''),
                'brand': brand,
                'vendor': item.get('article', ''),
                'barcode': [list(barcode.values())[0] for barcode in item.get('barcodes', [])],
                'product_type': item['meta'].get('type'),
                'price': wb_price_after_discount,
                'cost_price': cost_price,
            }
            product_data.append(product_info)

        # Массовая вставка или обновление данных
        with transaction.atomic():
            for product_info in product_data:
                ProductPrice.objects.update_or_create(
                    account=product_info['account'],
                    platform=product_info['platform'],
                    sku=product_info['sku'],
                    defaults=product_info
                )
