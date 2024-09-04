import logging

import requests
from django.db import transaction

from api_requests.moy_sklad import moy_sklad_assortment
from core.enums import MarketplaceChoices
from core.models import Account, Platform
from unit_economics.integrations import sender_error_to_tg
from unit_economics.models import (ProductForMarketplacePrice,
                                   ProductOzonPrice, ProductPrice)

logger = logging.getLogger(__name__)

OZON_ACCOUNT_NAME = {
    'ОЗОН Evium': 'Ozon Envium',
    'ОЗОН Combo': 'Озон Комбо',
    'ОЗОН Market Space': 'Озон спейс'
}


@sender_error_to_tg
def moy_sklad_add_data_to_db():
    """
    Записывает данные Мой Склад в базу данных

    Входящие переменные:
        TOKEN_MY_SKLAD - токен учетной записи
        account - объект модели Account
    """
    accounts_ms = Account.objects.filter(
        platform=Platform.objects.get(
            platform_type=MarketplaceChoices.MOY_SKLAD)
    )
    account_names = []
    accounts = Account.objects.all().values('name')
    for acc_obj in accounts:
        account_names.append(acc_obj['name'])

    for account in accounts_ms:
        token_ms = account.authorization_fields['token']
        products_data_list = moy_sklad_assortment(token_ms)
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
                    cost_price = item.get('buyPrice', {}).get(
                        'value', 0)  # Используем 0 как дефолтное значение

                elif item['meta']['type'] == 'bundle':
                    components_url = item['components']['meta']['href']
                    headers = {
                        'Authorization': f'Bearer {token_ms}',
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
                            response_url = requests.get(
                                product_url, headers=headers)

                            if response_url.status_code == 200:
                                cost_price_data = response_url.json()
                                total_cost_price += cost_price_data.get(
                                    'buyPrice', {}).get('value', 0) * quantity
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
                    'name': item.get('name', ''),
                    'brand': brand,
                    'vendor': item.get('article', ''),
                    'barcode': [list(barcode.values())[0] for barcode in item.get('barcodes', [])],
                    'product_type': item['meta'].get('type'),
                    'cost_price': cost_price,
                    'price_info': item['salePrices'],
                }
                product_data.append(product_info)

            # Массовая вставка или обновление данных
            with transaction.atomic():
                for product_info in product_data:
                    search_params = {'account': product_info['account'], 'name': product_info['name'],
                                     'vendor': product_info['vendor'], 'brand': product_info['brand']}
                    values_for_update = {
                        "barcode": product_info['barcode'],
                        "product_type": product_info['product_type'],
                        "cost_price": product_info['cost_price']
                    }
                    product_obj_сort = ProductPrice.objects.update_or_create(
                        defaults=values_for_update,
                        **search_params
                    )
                    product_obj = product_obj_сort[0]
                    price_for_marketplace_from_moysklad(
                        product_obj, product_info['price_info'], account_names)


@sender_error_to_tg
def price_for_marketplace_from_moysklad(product_obj, price_info, accounts_names):
    """"Записывает цены для маркетплейсов с Мой Склад"""
    rrc = 0
    wb_price = 0
    yandex_price = 0
    difficult_price_data = {}
    for data in price_info:
        if data['priceType']['name'] == 'Цена РРЦ МС':
            rrc = data['value'] / 100
        elif data['priceType']['name'] == 'Цена WB после скидки':
            wb_price = data['value'] / 100
        elif data['priceType']['name'] == 'Цена Яндекс После скидки':
            yandex_price = data['value'] / 100
        else:
            price_description = data['priceType']['name']
            price_account = ' '.join(price_description.split()[1:])
            if price_account in OZON_ACCOUNT_NAME:
                if OZON_ACCOUNT_NAME[price_account] in accounts_names:
                    difficult_price_data[OZON_ACCOUNT_NAME[price_account]
                                         ] = data['value']
    search_params = {'product': product_obj}
    values_for_update = {
        "wb_price": wb_price,
        "yandex_price": yandex_price,
        "rrc": rrc
    }
    ProductForMarketplacePrice.objects.update_or_create(
        defaults=values_for_update, **search_params
    )
    for account_name, price in difficult_price_data.items():
        search_params = {'product': product_obj,
                         'account': Account.objects.get(name=account_name)}
        values_for_update = {
            "ozon_price": price/100
        }
        ProductOzonPrice.objects.update_or_create(
            defaults=values_for_update, **search_params
        )
