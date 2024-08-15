import base64
import json

import requests
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from core.enums import MarketplaceChoices
from core.models import Account, Platform
from unit_economics.models import ProductPrice
from unit_economics.serializers import ProductPriceSerializer


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


class ProductPriceMSViewSet(ModelViewSet):
    """ViewSet для работы с продуктами на платформе МойСклад"""
    queryset = ProductPrice.objects.filter(platform=Platform.objects.get(platform_type=MarketplaceChoices.MOY_SKLAD))
    serializer_class = ProductPriceSerializer

    def list(self, request):
        """Получение данных о продуктах из API и обновление базы данных"""
        user = request.user

        try:
            account = Account.objects.filter(user=user).first()
        except Account.DoesNotExist:
            return Response({'status': 'error', 'message': 'Account not found for this user'},
                            status=status.HTTP_404_NOT_FOUND)

        limit = 100  # Количество товаров за один запрос
        offset = 0  # Начальная позиция
        total_processed = 0  # Счетчик обработанных записей

        while True:
            api_url = f"https://api.moysklad.ru/api/remap/1.2/entity/assortment?limit={limit}&offset={offset}&filter=archived=false;type=product;type=bundle"
            headers = {
                'Authorization': 'bfc927afe4d5353ed015687513d1351bc0a56bcb',
                'Accept-Encoding': 'gzip',
                'Content-Type': 'application/json'
            }
            response = requests.get(api_url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                products = data.get('rows', [])

                if not products:
                    break  # Если больше нет данных для обработки, выйти из цикла

                for item in products:
                    try:
                        # Создать или обновить запись в ProductPrice
                        obj, created = ProductPrice.objects.update_or_create(
                            account=account,
                            platform=Platform.objects.get(platform_type=MarketplaceChoices.MOY_SKLAD),
                            sku=item.get('id', ''),
                            defaults={
                                'name': item.get('name', ''),  # Имя товара
                                'brand': item.get('attributes', [{}])[0].get('value', None),  # Брэнд товара
                                'vendor': item.get('article', ''),  # Артикул товара
                                'barcode': item.get('barcodes', [{}])[0].get('ean13', ''),  # Баркод товара
                                'type': item['meta'].get('type'),  # Типо товара(товар, комплект товаров)
                                'price': item.get('salePrices', [{}])[0].get('value', None),  # Цена товара
                                'cost_price': item.get('buyPrice', {}).get('value', None),  # Себестоимость товара
                            }
                        )
                        total_processed += 1
                        print(f"{'Created' if created else 'Updated'}: {obj}")
                    except Exception as e:
                        print(f"Error processing item {item.get('id')}: {str(e)}")

                offset += limit  # Переход к следующему набору продуктов

            else:
                return Response({'status': 'error', 'message': response.text}, status=response.status_code)

        updated_products = ProductPrice.objects.filter(
            platform=Platform.objects.get(platform_type=MarketplaceChoices.MOY_SKLAD))
        serializer = ProductPriceSerializer(updated_products, many=True)
        return Response(
            {'status': 'success', 'message': f'Total processed: {total_processed}', 'data': serializer.data},
            status=status.HTTP_200_OK)


class ProductPriceWBViewSet(ModelViewSet):
    """ViewSet для работы с продуктами на платформе WB"""
    queryset = ProductPrice.objects.filter(platform=Platform.objects.get(platform_type=MarketplaceChoices.WILDBERRIES))
    serializer_class = ProductPriceSerializer

    def list(self, request):
        """Получение данных о продуктах из API и обновление базы данных"""
        user = request.user

        try:
            account = Account.objects.filter(user=user).first()
            if not account:
                raise Account.DoesNotExist
        except Account.DoesNotExist:
            return Response({'status': 'error', 'message': 'Account not found for this user'},
                            status=status.HTTP_404_NOT_FOUND)

        api_url = "https://suppliers-api.wildberries.ru/content/v2/get/cards/list"
        price_api_url = "https://discounts-prices-api.wildberries.ru/api/v2/list/goods/filter"
        headers = {
            'Authorization': 'eyJhbGciOiJFUzI1NiIsImtpZCI6IjIwMjQwODAxdjEiLCJ0eXAiOiJKV1QifQ.eyJlbnQiOjEsImV4cCI6MTczODI5MjgyMSwiaWQiOiI5NDQ5ZTg4ZC0zZTYxLTRlYzAtYTc2Yi04NzE3YTEzN2I4MGMiLCJpaWQiOjEwMjk2MTY1Niwib2lkIjoxMTkyMzQwLCJzIjoxMjYsInNpZCI6IjE0N2Y5YmQxLTZhZmEtNGIzYS1hMDg2LWQ4YzI0YTkzNmYxZCIsInQiOmZhbHNlLCJ1aWQiOjEwMjk2MTY1Nn0.8Beh_T8AH9BVY4dH_Zl5OW22lTjkDD-wJzfVArDv4ZnEgv5VFmqRnGTC8TLjCDuc_LRZ6HQecJRWRl2Nc1UGfw',
            'Content-Type': 'application/json'
        }

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

        total_processed = 0  # Счетчик обработанных записей

        while True:
            response = requests.post(api_url, headers=headers, data=json.dumps(request_body))

            if response.status_code == 200:
                data = response.json()
                products = data.get('cards', [])

                if not products:
                    break  # Если больше нет данных для обработки, выйти из цикла

                for item in products:
                    try:
                        nmID = item.get('nmID', '')
                        item_barcode = item.get('sizes', [{}])[0].get('skus'[0], '')

                        # Запрос для получения цены и скидки для конкретного товара
                        price_params = {
                            'filterNmID': nmID,
                            'limit': 1
                        }
                        price_response = requests.get(price_api_url, headers=headers, params=price_params)

                        if price_response.status_code == 200:
                            price_data = price_response.json()
                            list_goods = price_data.get('data', {}).get('listGoods', [{}])[0]
                            price = list_goods.get('price', None)  # Цена товара
                            discounted_price = list_goods.get('discountedPrice', None)  # Цена товара со скидкой
                        else:
                            print(
                                f"Error fetching price for nmID {nmID}: {price_response.status_code} - {price_response.text}")
                            price = None
                            discounted_price = None

                        # Получение cost_price из Мой Склад по баркоду
                        cost_price = ProductPrice.objects.filter(
                            platform=Platform.objects.get(platform_type=MarketplaceChoices.MOY_SKLAD),
                            barcode=item_barcode).first()
                        # Создать или обновить запись в ProductPrice
                        obj, created = ProductPrice.objects.update_or_create(
                            account=account,
                            platform=Platform.objects.get(platform_type=MarketplaceChoices.WILDBERRIES),
                            sku=item.get('nmID', ''),
                            defaults={
                                'name': item.get('title', ''),  # Имя товара
                                'brand': item.get('brand', ''),  # Брэнд товара
                                'vendor': item.get('vendorCode', ''),  # Артикул товара
                                'barcode': item.get('sizes', [{}])[0].get('skus', '')[0],  # Баркод товара
                                'type': item.get('nmID', ''),  # Артикул товара WB
                                'price': discounted_price,  # Цена товара со скидкой
                                'cost_price': discounted_price,  # Себестоимость товара из МойСклад
                            }
                        )
                        total_processed += 1
                        print(f"{'Created' if created else 'Updated'}: {obj}")
                    except Exception as e:
                        print(f"Error processing item {item.get('id')}: {str(e)}")

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
            else:
                print(f"Error: {response.status_code} - {response.text}")
                return Response({'status': 'error', 'message': response.text}, status=response.status_code)

        updated_products = ProductPrice.objects.filter(
            platform=Platform.objects.get(platform_type=MarketplaceChoices.WILDBERRIES))
        serializer = ProductPriceSerializer(updated_products, many=True)
        return Response(
            {'status': 'success', 'message': f'Total processed: {total_processed}', 'data': serializer.data},
            status=status.HTTP_200_OK)

# class ProductPriceViewSet(ModelViewSet):
#     """ViewSet для работы с продуктами"""
#     queryset = ProductPrice.objects.all()
#     serializer_class = ProductPriceSerializer
#
#     def list(self, request):
#         """Получение данных о продуктах из API и обновление базы данных"""
#         user = request.user
#
#         try:
#             account = Account.objects.filter(user=user)
#         except Account.DoesNotExist:
#             return Response({'status': 'error', 'message': 'Account not found for this user'},
#                             status=status.HTTP_404_NOT_FOUND)
#
#         limit = 100  # Количество товаров за один запрос
#         offset = 0  # Начальная позиция
#
#         api_url = f"https://api.moysklad.ru/api/remap/1.2/entity/assortment?filter=archived=false;type=product&bundle&limit={limit}&offset={offset}"
#         headers = {
#             'Authorization': 'bfc927afe4d5353ed015687513d1351bc0a56bcb',
#             'Accept-Encoding': 'gzip',
#             'Content-Type': 'application/json'
#         }
#         response = requests.get(api_url, headers=headers)
#         if response.status_code == 200:
#             data = response.json()
#             products = data.get('rows', [])
#
#             for item in products:
#                 try:
#                     # Найти продукт по SKU
#                     product = Product.objects.filter(sku=item['id']).first()  # `item['id']` используется как SKU
#                     print('wqdwqwdwq')
#                     if product is not None:
#                         # Создать или обновить запись в ProductPrice
#                         ProductPrice.objects.update_or_create(
#                             product=product,
#                             platform=Platform.objects.get(platform_type=MarketplaceChoices.MOY_SKLAD),
#                             defaults={
#                                 'price': item.get('salePrices', [{}])[0].get('value', None),
#                                 'cost_price': item.get('buyPrice', {}).get('value', None),
#                             }
#                         )
#                 except Product.DoesNotExist:
#                     # Пропустить если продукт с таким SKU не найден
#                     continue
#             offset += limit  # Переход к следующему набору продукт
#             return Response({'status': 'success', 'data': products}, status=status.HTTP_200_OK)
#         else:
#             return Response({'status': 'error', 'message': response.text}, status=response.status_code)

# def update(self, request, pk=None):
#     """Обновление цены продукта"""
#     try:
#         product = self.get_object(pk)
#         new_price = request.data.get('price')
#
#         if new_price is not None:
#             product.price = new_price  # Обновляем цену
#             product.save()
#
#             # Отправка обновления на сервис Мой Склад
#             api_url = f"https://api.moysklad.ru/api/remap/1.2/entity/product/{product.sku}"
#             headers = {
#                 'Authorization': f"Bearer {product.account.authorization_fields['token']}",
#                 'Content-Type': 'application/json'
#             }
#             payload = {
#                 'price': new_price
#             }
#             response = requests.put(api_url, json=payload, headers=headers)
#
#             if response.status_code == 200:
#                 return Response({'status': 'success', 'message': 'Price updated successfully'},
#                                 status=status.HTTP_200_OK)
#             else:
#                 return Response({'status': 'error', 'message': response.text}, status=response.status_code)
#         else:
#             return Response({'status': 'error', 'message': 'Price not provided'},
#                             status=status.HTTP_400_BAD_REQUEST)
#
#     except ProductPrice.DoesNotExist:
#         return Response({'status': 'error', 'message': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

# class MySkladProduct():
#     auth_fields_description = {
#         "login": {"name": "Логин", "type": FieldsTypes.TEXT, "max_length": 255},
#         "password": {"name": "Пароль", "type": FieldsTypes.PASSWORD, "max_length": 255},
#     }
#
#     def get_auth_token(self):
#         return (
#             self.account.authorization_fields.get("login", ""),
#             self.account.authorization_fields.get("password", ""),
#         )
#
#     def get_products(self) -> List[dict] or None:
#         session = requests.Session()
#         session.auth = self.get_auth_token()
#         resp = session.get("https://api.moysklad.ru/api/remap/1.2/entity/product")
#         if resp.status_code != 200:
#             return None
#
#         rows = resp.json().get("rows")
#         if not rows:
#             return None
#
#         all_items = []
#
#         for row in rows:
#             if row.get("barcodes"):
#                 for barcode_data in row.get("barcodes"):
#                     for key in barcode_data:
#                         all_items.append(
#                             {"barcode": barcode_data[key], "sku": row["id"], "vendor": row["code"], "name": row["name"]}
#                         )
#
#         return all_items
