import logging

import requests
from django.db import transaction

from api_requests.moy_sklad import (get_assortiment_info,
                                    get_picture_from_moy_sklad, get_stock_info,
                                    moy_sklad_assortment, moy_sklad_bundle_components, moy_sklad_enter,
                                    moy_sklad_positions_enter, moy_sklad_product_info,
                                    picture_href_request)
from core.enums import MarketplaceChoices
from core.models import Account, Platform
# from unit_economics.integrations import sender_error_to_tg
from unit_economics.models import (PostingGoods, ProductCostPrice,
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
                code = item.get('code', '')
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
                                product_url, headers=headers, timeout=60)

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
                if cost_price:
                    common_cost_price = cost_price/100
                else:
                    common_cost_price = 0

                if ProductPrice.objects.filter(
                        account=account,
                        moy_sklad_product_number=item.get('id', '')).exists():
                    ProductPrice.objects.filter(
                        account=account,
                        moy_sklad_product_number=item.get('id', '')).update(
                        name=item.get('name', ''),
                        code=code,
                        barcode=[list(barcode.values())[0]
                                 for barcode in item.get('barcodes', [])],
                        cost_price=common_cost_price,
                        brand=brand,
                        vendor=item.get('article', '')
                    )
                else:
                    ProductPrice(
                        account=account,
                        moy_sklad_product_number=item.get('id', ''),
                        code=code,
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
    Записывает поставки товаров Их Моего Склада в базу данных
    Считает поставки товара на Мой Склад.

    Возвращает словарь вида:
    {account:
        {code:
            {
                'article_data': {'moy_sklad_id: moy_sklad_id}, 
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
        moy_sklad_id - id товара в Мой Склад
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
        enters_list_raw = moy_sklad_enter(token_ms)
        enters_list = sorted(
            enters_list_raw, key=lambda x: x['moment'], reverse=True)
        enter_main_data = {}
        # print(len(enters_list))

        x = len(enters_list)
        print(len(enters_list))
        for enter in enters_list:
            enter_id = enter['id']
            x -= 1
           
            if PostingGoods.objects.filter(enter_number=enter_id).exists():
                print('Должен пропустить')
                continue
            else:
                if 'moment' in enter:
                    enter_date = enter['moment']
                    positions = moy_sklad_positions_enter(token_ms, enter_id)
                    for position in positions:
                        position_id = position['id']
                        if PostingGoods.objects.filter(position_number=position_id).exists():
                            continue
                        else:
                            api_url = position['assortment']['meta']['href']
                            assortiment_data = get_assortiment_info(
                                token_ms, api_url)
                            if assortiment_data:
                                if assortiment_data['archived'] == False:
                                    moy_sklad_id = assortiment_data['id']
                                    quantity = position.get('quantity', 0)
                                    price = position.get('price', 0)
                                    overhead = position.get('overhead', 0)

                                    if 'code' in assortiment_data and quantity != 0 and price != 0:
                                        article = assortiment_data['code']
                                        if ProductPrice.objects.filter(moy_sklad_product_number=moy_sklad_id).exists():
                                            product_obj = ProductPrice.objects.get(
                                                moy_sklad_product_number=moy_sklad_id)

                                            PostingGoods(
                                                account=account,
                                                enter_number=enter_id,
                                                position_number=position_id,
                                                product=product_obj,
                                                code=article,
                                                receipt_date=enter_date,
                                                amount=quantity,
                                                price=price,
                                                costs=overhead
                                            ).save()
                                            # if article not in enter_main_data:
                                            #     enter_main_data[article] = {
                                            #         'article_data':
                                            #             {
                                            #                 'moy_sklad_id': moy_sklad_id
                                            #             },
                                            #         'enter_data': [
                                            #             {
                                            #                 'date': enter_date,
                                            #                 'price': price,
                                            #                 'quantity': quantity,
                                            #                 'overhead': overhead
                                            #             }]}
                                            # else:
                                            #     enter_main_data[article]['enter_data'].append({
                                            #         'date': enter_date,
                                            #         'price': price,
                                            #         'quantity': quantity,
                                            #         'overhead': overhead
                                            #     })
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
                    stocks_data[code] = stock
        main_retuned_dict[account] = stocks_data

    # print(main_retuned_dict)
    return main_retuned_dict


# @sender_error_to_tg
def moy_sklad_costprice_calculate():
    """
    Считает себестоимость товаров методом оприходования
    """
    enters_data = moy_sklad_enters_calculate()
    stock_data = moy_sklad_stock_data()
    enters_data = {}
    account_cost_price_data = {}
    main_data = PostingGoods.objects.all()
    for data in main_data:
        inner_dict = {
            'date': data.receipt_date,
            'price': data.price,
            'quantity': data.amount,
            'overhead': data.costs
        }
        if data.account not in enters_data:
            enters_data[data.account] = {
                data.code: {
                    'article_data': {
                        'product': data.product
                    },
                    'enter_data': [inner_dict]
                }
            }
        else:
            if data.code not in enters_data[data.account]:
                enters_data[data.account][data.code] = {
                    'article_data': {
                        'product': data.product
                    },
                    'enter_data': [inner_dict]
                }

            else:
                if inner_dict not in enters_data[data.account][data.code]['enter_data']:
                    enters_data[data.account][data.code]['enter_data'].append(
                        inner_dict)

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
            for index, enter_data in enumerate(sorted_enters_data_list):
                summ += enter_data['quantity']
                if code in stock_data[account]:
                    if summ >= stock_data[account][code]:
                        overhead = enter_data['overhead']
                        amount = enter_data['quantity']
                        price = enter_data['price']
                        continue
                    elif summ < stock_data[account][code] and index == len(sorted_enters_data_list) - 1:
                        overhead = enter_data['overhead']
                        amount = enter_data['quantity']
                        price = enter_data['price']

            if amount > 0:
                cost_price = (price + overhead/amount) / 100
                inner_dict = {
                    'product': article_info['article_data']['product'], 'cost_price': cost_price}
                code_list.append(inner_dict)
        account_cost_price_data[account] = code_list
    return account_cost_price_data

def moy_sklad_costprice_calculate_for_bundle():
    """
    Считает себестоимость товаров методом оприходования для комплектов
    """
    accounts_ms = Account.objects.filter(
        platform=Platform.objects.get(
            platform_type=MarketplaceChoices.MOY_SKLAD)
    )
    stock_data = moy_sklad_stock_data()
    for account in accounts_ms:
        token_ms = account.authorization_fields['token']
        

        products_list = ProductPrice.objects.filter(product_type='bundle')
        stock_account = stock_data[account]
        ids_code_bundle_list = {}
        for data in products_list:
            components = moy_sklad_bundle_components(token_ms, data.moy_sklad_product_number)
            component_list = []
            data_costprice = 0
            for component in components:
                product_link  =component['assortment']['meta']['href']
                component_data = moy_sklad_product_info(token_ms, product_link)
                component_moy_sklad_product_number = component_data['id']
                component_code = component_data['code']
                component_amount = component['quantity']
                component_costprice = 0
                component_enter_data = PostingGoods.objects.filter(product__moy_sklad_product_number=component_moy_sklad_product_number).order_by('-receipt_date')
                # print('component_code', component_code)
                # print('component_enter_data', component_enter_data)
                for index, component_enter in enumerate(component_enter_data):    
                    if component_code in stock_account:
                        code_stock = stock_account[component_code]
                        common_amount = 0

                        # for component_enter in component_enter_data:
                        common_amount += component_enter.amount
                        if common_amount > code_stock:
                            component_costprice = component_enter.price + component_enter.costs/component_enter.amount
                        elif common_amount < code_stock and index == len(component_enter_data) - 1:
                            component_costprice = component_enter.price + component_enter.costs/component_enter.amount
                        
                    else:
                        component_costprice = component_enter.price + component_enter.costs/component_enter.amount
                
                # print(component_code, component_costprice/100)
                data_costprice += component_costprice/100 * component_amount

            print(data, data_costprice)
            
        cp_obj = ProductCostPrice.objects.get(product=data)
        cp_obj.cost_price = round(data_costprice, 2)
        cp_obj.save()
