import logging

import requests
from django.db import transaction

from api_requests.moy_sklad import (get_assortiment_info,
                                    get_picture_from_moy_sklad, get_stock_info,
                                    moy_sklad_assortment, moy_sklad_enter,
                                    moy_sklad_positions_enter,
                                    picture_href_request)
from core.enums import MarketplaceChoices
from core.models import Account, Platform
# from unit_economics.integrations import sender_error_to_tg
from unit_economics.models import (ProductCostPrice,
                                   ProductForMarketplacePrice,
                                   ProductOzonPrice, ProductPrice)

logger = logging.getLogger(__name__)

OZON_ACCOUNT_NAME = {
    'ОЗОН Evium': 'Ozon Envium',
    'ОЗОН Combo': 'Озон Комбо',
    'ОЗОН Market Space': 'Озон спейс'
}


# @sender_error_to_tg
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
                # Добавление фотографии
                # photo_link = picture_href_request(
                #     token_ms, item['images']['meta']['href'])
                image_filename = ''
                image_content = ''
                # if photo_link:
                #     image_filename, image_content = get_picture_from_moy_sklad(
                #         token_ms, photo_link)

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

                    response = requests.get(
                        components_url, headers=headers, timeout=10)

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
                common_cost_price = cost_price/100
                if "c1d9c73a-d82f-11ed-0a80-0b960080d4cb" in item.get('id'):
                    print('cost_price', cost_price, common_cost_price)

                if ProductPrice.objects.filter(
                        account=account,
                        barcode=[list(barcode.values())[0]
                                 for barcode in item.get('barcodes', [])],
                        moy_sklad_product_number=item.get('id', '')).exists():
                    ProductPrice.objects.filter(
                        account=account,
                        barcode=[list(barcode.values())[0]
                                 for barcode in item.get('barcodes', [])],
                        moy_sklad_product_number=item.get('id', '')).update(
                        name=item.get('name', ''),
                        cost_price=common_cost_price,
                        brand=brand,
                        vendor=item.get('article', '')
                    )
                else:
                    ProductPrice(
                        account=account,
                        moy_sklad_product_number=item.get('id', ''),
                        name=item.get('name', ''),
                        brand=brand,
                        vendor=item.get('article', ''),
                        barcode=[list(barcode.values())[0]
                                 for barcode in item.get('barcodes', [])],
                        product_type=item['meta'].get('type'),
                        cost_price=common_cost_price
                    ).save()

                product_obj = ProductPrice.objects.get(
                    account=account,
                    barcode=[list(barcode.values())[0]
                             for barcode in item.get('barcodes', [])],
                    moy_sklad_product_number=item.get('id', ''))
                price_for_marketplace_from_moysklad(
                    product_obj, item['salePrices'], account_names)
                if image_filename:
                    product_obj.image.save(
                        image_filename, image_content)
                # product_info = {
                #     'account': account,
                #     'moy_sklad_product_number': item.get('id', ''),
                #     'name': item.get('name', ''),
                #     'brand': brand,
                #     'vendor': item.get('article', ''),
                #     'barcode': [list(barcode.values())[0] for barcode in item.get('barcodes', [])],
                #     'product_type': item['meta'].get('type'),
                #     'cost_price': common_cost_price,
                #     'price_info': item['salePrices'],
                #     'image_filename': image_filename,
                #     'image_content': image_content
                # }
                # product_data.append(product_info)

            # Массовая вставка или обновление данных
            # for product_info in product_data:
            #     search_params = {'account': product_info['account'], "barcode": product_info['barcode'], "moy_sklad_product_number": product_info['moy_sklad_product_number'],
            #                      }
            #     values_for_update = {
            #         "name": product_info['name'],
            #         "product_type": product_info['product_type'],
            #         "cost_price": product_info['cost_price'],
            #         'brand': product_info['brand'],
            #         "vendor": product_info['vendor']
            #     }
            #     product_obj_сort = ProductPrice.objects.update_or_create(
            #         account=product_info['account'],
            #         barcode=product_info['barcode'],
            #         moy_sklad_product_number=product_info['moy_sklad_product_number'],
            #         defaults=values_for_update
            #     )
            #     product_obj = product_obj_сort[0]
            #     price_for_marketplace_from_moysklad(
            #         product_obj, product_info['price_info'], account_names)
            #     if product_info['image_content']:
            #         product_obj.image.save(
            #             product_info['image_filename'], product_info['image_content'])


# @sender_error_to_tg
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
                                         ] = data['value']/100
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
            "ozon_price": price
        }
        ProductOzonPrice.objects.update_or_create(
            defaults=values_for_update, **search_params
        )


# @sender_error_to_tg
def moy_sklad_enters_calculate():
    """
    Считает поставки товара на Мой Склад.

    Возвращает словарь вида:
    {account:
        {code:
            {
                'article_data': {'barcodes: [barcode_list], 'brand': brand}, 
                'enter_data': {
                    [
                        {
                            'date': enter_date,
                            'price': price,
                            'quantity': quantity,
                            'overhead': overhead
                        }
                    ]
                }
            }
        }
    }

    Где:
        account - текущий аккаунт на Мой Склад
        code - обозначение артикула в Мой Склад
        [barcode_list] - список баркодов артикулов в Мой Склад
        brand - бренд артикула
        enter_date - дата поставки
        price - стоимость поставки
        quantity - количество артикула в текущей поставке
        overhead - Накладные расходы
    """
    accounts_ms = Account.objects.filter(
        platform=Platform.objects.get(
            platform_type=MarketplaceChoices.MOY_SKLAD)
    )
    main_retuned_dict = {}
    for account in accounts_ms:
        token_ms = account.authorization_fields['token']
        enters_list = moy_sklad_enter(token_ms)

        enter_main_data = {}
        # print(len(enters_list))

        # x = len(enters_list)
        for enter in enters_list:
            enter_id = enter['id']
            if 'moment' in enter:
                enter_date = enter['moment']
                positions = moy_sklad_positions_enter(token_ms, enter_id)
                for position in positions:
                    barcodes = []
                    api_url = position['assortment']['meta']['href']
                    assortiment_data = get_assortiment_info(
                        token_ms, api_url)
                    if assortiment_data:
                        if assortiment_data['archived'] == False:
                            quantity = position.get('quantity', 0)
                            price = position.get('price', 0)
                            overhead = position.get('overhead', 0)
                            article = assortiment_data['code']

                            if 'barcodes' in assortiment_data:
                                barcode_list = assortiment_data['barcodes']
                                for barcode_data in barcode_list:
                                    for key, barcode in barcode_data.items():
                                        barcodes.append(barcode)
                            attributes = assortiment_data['attributes']
                            for attribute in attributes:
                                if attribute['name'] == 'Бренд':
                                    brand = attribute['value']

                            if article not in enter_main_data:
                                enter_main_data[article] = {
                                    'article_data':
                                        {
                                            'barcodes': barcodes,
                                            'brand': brand
                                        },
                                    'enter_data': [
                                        {
                                            'date': enter_date,
                                            'price': price,
                                            'quantity': quantity,
                                            'overhead': overhead
                                        }]}
                            else:
                                enter_main_data[article]['enter_data'].append({
                                    'date': enter_date,
                                    'price': price,
                                    'quantity': quantity,
                                    'overhead': overhead
                                })
            # x -= 1
            # print(x)
        main_retuned_dict[account] = enter_main_data
    return main_retuned_dict


# @sender_error_to_tg
def moy_sklad_stock_data():
    """
    Возвращает информацию об остатках товара на Мой Склад.

    Возвращает словарь вида:
    {account: {code: stock}}

    Где:
        account - текущий аккаунт на Мой Склад
        code - обозначение артикула в Мой Склад
        stock - текущий остаток артикула
    """
    accounts_ms = Account.objects.filter(
        platform=Platform.objects.get(
            platform_type=MarketplaceChoices.MOY_SKLAD)
    )
    main_retuned_dict = {}
    for account in accounts_ms:
        token_ms = account.authorization_fields['token']
        stocks_list = get_stock_info(token_ms)
        stocks_data = {}
        for stock_data in stocks_list:
            if 'code' in stock_data:
                code = stock_data['code']
                if 'stock' in stock_data:
                    stock = stock_data['stock']
                else:
                    stock = 0
                stocks_data[code] = stock
        main_retuned_dict[account] = stocks_data
    return main_retuned_dict


# @sender_error_to_tg
def moy_sklad_costprice_calculate():
    """
    Считает себестоимость товаров методом оприходования
    """
    enters_data = moy_sklad_enters_calculate()
    stock_data = moy_sklad_stock_data()

    account_cost_price_data = {}

    for account, code_data in enters_data.items():
        code_list = []
        for code, article_info in code_data.items():
            enters_data_list = article_info['enter_data']
            sorted_enters_data_list = sorted(
                enters_data_list, key=lambda x: x['date'], reverse=True)
            summ = 0
            amount = 0
            overhead = 0
            price = 0
            for enter_data in sorted_enters_data_list:
                summ += enter_data['quantity']
                if code in stock_data[account]:
                    if summ > stock_data[account][code]:
                        overhead = enter_data['overhead']
                        amount = enter_data['quantity']
                        price = enter_data['price']
                        break
            if amount > 0:
                cost_price = (price + overhead) / (amount * 100)
            else:
                cost_price = 0
            inner_dict = {'barcodes': article_info['article_data']
                          ['barcodes'], 'cost_price': cost_price}
            code_list.append(inner_dict)
        account_cost_price_data[account] = code_list
    return account_cost_price_data
