import logging

import requests
from django.db import transaction
from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from analyticalplatform.settings import (OZON_ID, TOKEN_MY_SKLAD, TOKEN_OZON,
                                         TOKEN_WB, TOKEN_YM)
from core.enums import MarketplaceChoices
from core.models import Account, Platform
from unit_economics.models import ProductPrice
from unit_economics.serializers import ProductPriceSerializer
from unit_economics.tasks_moy_sklad import moy_sklad_add_data_to_db
from unit_economics.tasks_ozon import (ozon_comission_logistic_add_data_to_db,
                                       ozon_products_data_to_db)
from unit_economics.tasks_wb import (wb_categories_list,
                                     wb_comission_add_to_db,
                                     wb_logistic_add_to_db,
                                     wb_products_data_to_db)
from unit_economics.tasks_yandex import (
    yandex_add_products_data_to_db, yandex_business_list,
    yandex_comission_logistic_add_data_to_db)

logger = logging.getLogger(__name__)


# def moysklad_json_token():
#     """Получение JSON токена"""
#     BASE_URL = 'https://api.moysklad.ru/api/remap/1.2'
#     TOKEN = '/security/token/'
#     url = f'{BASE_URL}{TOKEN}'
#
#     # Указываем логин и пароль
#     username = 'rauhelper@yandex.ru'
#     password = 'preprod123'
#
#     # Кодируем логин и пароль в base64 для заголовка Authorization
#     auth_str = f'{username}:{password}'
#     auth_bytes = auth_str.encode('ascii')
#     auth_base64 = base64.b64encode(auth_bytes).decode('ascii')
#
#     payload = {}
#
#     # Создаем заголовки для запроса
#     headers = {
#         'Authorization': f'Basic {auth_base64}',
#         'Content-Type': 'application/json'
#     }
#
#     # Выполняем POST запрос
#     response = requests.request("POST", url, headers=headers, data=payload)
#
#     if 200 <= response.status_code < 300:
#         token = response.json()['access_token']
#         return token
#     return None


class ProductPriceMSViewSet(viewsets.ViewSet):
    """ViewSet для работы с продуктами на платформе МойСклад"""
    # queryset = ProductPrice.objects.filter(platform=Platform.objects.get(platform_type=MarketplaceChoices.MOY_SKLAD))
    queryset = ProductPrice.objects.all()
    serializer_class = ProductPriceSerializer

    def list(self, request):
        """Получение данных о продуктах из API и обновление базы данных"""
        user = request.user

        account, created = Account.objects.get_or_create(
            user=user,
            platform=Platform.objects.get(
                platform_type=MarketplaceChoices.MOY_SKLAD),
            defaults={
                'name': 'Мой склад',
                'authorization_fields': {'token': TOKEN_MY_SKLAD}
            }
        )
        # Если аккаунт уже существует, но токен не установлен, обновите его
        if not created and account.authorization_fields.get('token') != TOKEN_MY_SKLAD:
            account.authorization_fields['token'] = TOKEN_MY_SKLAD
            account.save()
        total_processed = 0  # Счетчик обработанных записей

        # wb_products_data_to_db()
        # wb_logistic_add_to_db()
        # wb_comission_add_to_db()

        # ozon_products_data_to_db()
        # ozon_comission_logistic_add_data_to_db()

        # yandex_add_products_data_to_db()
        # yandex_comission_logistic_add_data_to_db()

        # moy_sklad_add_data_to_db()
        updated_products = ProductPrice.objects.all()
        serializer = ProductPriceSerializer(updated_products, many=True)
        return Response(
            {'status': 'success', 'message': f'Total processed: {total_processed}',
                'data': serializer.data},
            status=status.HTTP_200_OK)


class ProductPriceWBViewSet(ModelViewSet):
    """ViewSet для работы с продуктами на платформе WB"""
    # queryset = ProductPrice.objects.filter(platform=Platform.objects.get(platform_type=MarketplaceChoices.WILDBERRIES))
    queryset = ProductPrice.objects.all()
    serializer_class = ProductPriceSerializer

    def list(self, request):
        """Получение данных о продуктах из API и обновление базы данных"""
        user = request.user
        account, created = Account.objects.get_or_create(
            user=user,
            platform=Platform.objects.get(
                platform_type=MarketplaceChoices.WILDBERRIES),
            defaults={
                'name': 'Магазин WB',
                'authorization_fields': {'token': TOKEN_WB}
            }
        )
        # Если аккаунт уже существует, но токен не установлен, обновите его
        if not created and account.authorization_fields.get('token') != TOKEN_WB:
            account.authorization_fields['token'] = TOKEN_WB
            account.save()
        # Начальные параметры запроса
        request_body = {
            "settings": {
                "cursor": {
                    "limit": 100
                },
                "filter": {
                    "withPhoto": -1
                }
            }
        }
        all_product_data = []  # Для сбора всех данных о продуктах
        while True:
            api_url = "https://content-api.wildberries.ru/content/v2/get/cards/list"
            headers = {
                'Authorization': f"Bearer {TOKEN_WB}",
                'Content-Type': 'application/json'
            }

            product_data = []  # Список для хранения данных о продуктах
            response = requests.post(
                api_url, headers=headers, json=request_body)
            if response.status_code == 200:
                data = response.json()
                products = data.get('cards', [])
                if not products:
                    break  # Если больше нет данных для обработки, выйти из цикла
                for item in products:
                    # Добавляем продукты и информацию о них в список
                    product_info = {
                        'account': account,
                        'platform': Platform.objects.get(platform_type=MarketplaceChoices.WILDBERRIES),
                        'sku': item.get('nmID', ''),
                        'name': item.get('title', ''),  # Имя товара
                        'brand': item.get('brand', ''),  # Брэнд товара
                        'vendor': item.get('vendorCode', ''),  # Артикул товара
                        # Баркод товара
                        'barcode': item.get('sizes', [{}])[0].get('skus', '')[0],
                        'type': '',  # Артикул товара WB
                        'price': 0,  # Цена товара со скидкой
                        'cost_price': 0,  # Себестоимость товара из МойСклад
                    }

                    moy_sklad_product = ProductPrice.objects.filter(
                        platform=Platform.objects.get(
                            platform_type=MarketplaceChoices.MOY_SKLAD),
                        barcode__contains=product_info['barcode']).first()
                    if moy_sklad_product is not None:
                        product_info['price'] = moy_sklad_product.price
                        product_info['cost_price'] = moy_sklad_product.cost_price
                    else:
                        print(
                            f"Product with barcode {product_info['barcode']} not found in MoySklad")
                    product_data.append(product_info)

                # Добавляем данные в общий список
                all_product_data.extend(product_data)

                # Параметры пагинации
                cursor = data.get('cursor', {})
                updatedAt = cursor.get('updatedAt')
                nmID = cursor.get('nmID')

                if not updatedAt or not nmID:
                    break  # Если пагинация закончена, выйти из цикла

                request_body['settings']['cursor'] = {
                    "limit": 100,
                    "updatedAt": updatedAt,
                    "nmID": nmID
                }

                # Обновление существующих записей или создание новых
                with transaction.atomic():
                    for product_info in all_product_data:
                        ProductPrice.objects.update_or_create(
                            account=product_info['account'],
                            platform=product_info['platform'],
                            sku=product_info['sku'],
                            defaults=product_info
                        )

        updated_products = ProductPrice.objects.filter(
            platform=Platform.objects.get(platform_type=MarketplaceChoices.WILDBERRIES))
        serializer = ProductPriceSerializer(updated_products, many=True)
        return Response(
            {'status': 'success', 'data': serializer.data},
            status=status.HTTP_200_OK)


# class ProductPriceOZONViewSet(ModelViewSet):
#     """ViewSet для работы с продуктами на платформе Ozon"""
#     queryset = ProductPrice.objects.filter(
#         platform=Platform.objects.get(platform_type=MarketplaceChoices.OZON))
#     serializer_class = ProductPriceSerializer
#
#     def list(self, request):
#         """Получение данных о продуктах из API и обновление базы данных"""
#         user = request.user
#         platform = Platform.objects.get(platform_type=MarketplaceChoices.OZON)
#
#         # Получаем все аккаунты для данного пользователя и платформы
#         accounts = Account.objects.filter(user=user, platform=platform)
#
#         # Проверяем каждый аккаунт на соответствие поля authorization_fields
#         account = None
#         for acc in accounts:
#             auth_fields = acc.authorization_fields
#             if auth_fields.get('token') == TOKEN_OZON and auth_fields.get('client_id') == OZON_ID:
#                 account = acc
#                 break
#
#         # Если соответствующий аккаунт не найден, создаем новый
#         if account is None:
#             account = Account.objects.create(
#                 user=user,
#                 platform=platform,
#                 name='Магазин Ozon',
#                 authorization_fields={'token': TOKEN_OZON, 'client_id': OZON_ID}
#             )
#         while True:
#             api_url = "https://api-seller.ozon.ru/v2/product/list?filter=\"visibility\": \"ALL\"&limit=1000"
#             headers = {
#                 'Client-Id': OZON_ID,
#                 'Api-Key': TOKEN_OZON
#             }
#
#             product_data = []  # Список для хранения данных о продуктах
#             response = requests.post(api_url, headers=headers)
#             if response.status_code == 200:
#                 data = response.json()
#                 products = data.get("result", {}).get("items", [])
#                 products_ids = [product["product_id"] for product in products]
#                 print(len(products_ids))
#                 for product_id in products_ids:
#                     response_info = requests.post("https://api-seller.ozon.ru/v2/product/info/list",
#                                                   json={"product_id": [product_id]}, headers=headers)
#                     if response_info.status_code != 200:
#                         return Response({'status': 'error', 'message': 'Failed to get product info'},
#                                         status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#                     response_info = response_info.json().get("result", {}).get("items", [])
#                     if response_info:
#                         # Поскольку это список, берем первый элемент
#                         product_info = response_info[0]
#                         # Добавляем продукты и информацию о них в список
#                         product_info_item = {
#                             'account': account,
#                             'platform': Platform.objects.get(platform_type=MarketplaceChoices.OZON),
#                             'sku': product_info.get('sku', ''),
#                             'name': product_info.get('name', ''),  # Имя товара
#                             'brand': product_info.get('offer_id', ''),  # Брэнд товара
#                             'vendor': '',  # Артикул товара
#                             'barcode': product_info.get('barcode', ''),  # Баркод товара
#                             'type': '',  # Тип товара
#                             'price': 0,  # Цена товара со скидкой
#                             'cost_price': 0,  # Себестоимость товара из МойСклад
#                         }
#                         print(f"111111: {product_info_item}")
#                         moy_sklad_product = ProductPrice.objects.filter(
#                             platform=Platform.objects.get(platform_type=MarketplaceChoices.MOY_SKLAD),
#                             barcode__contains=product_info_item['barcode']).first()
#                         if moy_sklad_product is not None:
#                             product_info_item['price'] = moy_sklad_product.price
#                             product_info_item['cost_price'] = moy_sklad_product.cost_price
#                         else:
#                             print(f"Product with barcode {product_info_item['barcode']} not found in MoySklad")
#                         print(f"Количество объектов для записи: {len(product_data)}")
#                         product_data.append(product_info_item)
#
#             # Обновление существующих записей или создание новых
#                 with transaction.atomic():
#                     for product_info_item in product_data:
#                         ProductPrice.objects.update_or_create(
#                             account=product_info_item['account'],
#                             platform=product_info_item['platform'],
#                             sku=product_info_item['sku'],
#                             defaults=product_info_item
#                         )
#                         print(7)
#
#             updated_products = ProductPrice.objects.filter(
#                 platform=Platform.objects.get(platform_type=MarketplaceChoices.OZON))
#             serializer = ProductPriceSerializer(updated_products, many=True)
#             return Response(
#                 {'status': 'success', 'data': serializer.data},
#                 status=status.HTTP_200_OK)

class ProductPriceOZONViewSet(ModelViewSet):
    # queryset = ProductPrice.objects.filter(
    #     platform=Platform.objects.get(platform_type=MarketplaceChoices.OZON))
    queryset = ProductPrice.objects.all()
    serializer_class = ProductPriceSerializer

    def list(self, request):
        user = request.user
        platform = Platform.objects.get(platform_type=MarketplaceChoices.OZON)
        accounts = Account.objects.filter(user=user, platform=platform)

        account = None
        for acc in accounts:
            auth_fields = acc.authorization_fields
            if auth_fields.get('token') == TOKEN_OZON and auth_fields.get('client_id') == OZON_ID:
                account = acc
                break

        if account is None:
            account = Account.objects.create(
                user=user,
                platform=platform,
                name='Магазин Ozon',
                authorization_fields={
                    'token': TOKEN_OZON, 'client_id': OZON_ID}
            )

        product_data = []  # Список для хранения данных о продуктах

        api_url = "https://api-seller.ozon.ru/v2/product/list?filter=\"visibility\": \"ALL\"&limit=1000"
        headers = {
            'Client-Id': OZON_ID,
            'Api-Key': TOKEN_OZON
        }

        response = requests.post(api_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            products = data.get("result", {}).get("items", [])
            products_ids = [product["product_id"] for product in products]
            response_info = requests.post("https://api-seller.ozon.ru/v2/product/info/list",
                                          json={"product_id": products_ids}, headers=headers)
            response_info = response_info.json().get("result", {}).get("items", [])
            print(response_info)
            for product in response_info:
                product_info_item = {
                    'account': account,
                    'platform': Platform.objects.get(platform_type=MarketplaceChoices.OZON),
                    'sku': product.get('sku', ''),
                    'name': product.get('name', ''),
                    'brand': product.get('offer_id', ''),
                    'vendor': '',
                    'barcode': product.get('barcode', ''),
                    'type': '',
                    'price': 0,
                    'cost_price': 0,
                }
                moy_sklad_product = ProductPrice.objects.filter(
                    platform=Platform.objects.get(
                        platform_type=MarketplaceChoices.MOY_SKLAD),
                    barcode__contains=product_info_item['barcode']).first()
                if moy_sklad_product:
                    product_info_item['price'] = moy_sklad_product.price
                    product_info_item['cost_price'] = moy_sklad_product.cost_price
                else:
                    print(
                        f"Product with barcode {product_info_item['barcode']} not found in MoySklad")
                print(f"Количество объектов для записи: {len(product_data)}")
                product_data.append(product_info_item)

    # Обновление существующих записей или создание новых
        with transaction.atomic():
            for product_info_item in product_data:
                ProductPrice.objects.update_or_create(
                    account=product_info_item['account'],
                    platform=product_info_item['platform'],
                    sku=product_info_item['sku'],
                    defaults=product_info_item
                )

        updated_products = ProductPrice.objects.filter(
            platform=Platform.objects.get(platform_type=MarketplaceChoices.OZON))
        serializer = ProductPriceSerializer(updated_products, many=True)
        return Response(
            {'status': 'success', 'data': serializer.data},
            status=status.HTTP_200_OK)


class ProductMoySkladViewSet(ModelViewSet):
    # queryset = (ProductPrice.objects.filter(platform=Platform.objects.get(platform_type=MarketplaceChoices.MOY_SKLAD))
    #             .annotate(product_count=Count('id')))
    queryset = (ProductPrice.objects.all()
                .annotate(product_count=Count('id')))
    serializer_class = ProductPriceSerializer


class ProductWBViewSet(ModelViewSet):
    # queryset = (ProductPrice.objects.filter(platform=Platform.objects.get(platform_type=MarketplaceChoices.WILDBERRIES))
    #             .annotate(product_count=Count('id')))
    queryset = (ProductPrice.objects.all()
                .annotate(product_count=Count('id')))
    serializer_class = ProductPriceSerializer


class ProductOZONViewSet(ModelViewSet):
    # queryset = (ProductPrice.objects.filter(platform=Platform.objects.get(platform_type=MarketplaceChoices.OZON))
    #             .annotate(product_count=Count('id')))
    queryset = (ProductPrice.objects.all()
                .annotate(product_count=Count('id')))
    serializer_class = ProductPriceSerializer
