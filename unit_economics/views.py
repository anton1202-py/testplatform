import base64

import requests
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.integrations import MyWarehouseIntegration
from core.models import Account, Product
from unit_economics.models import ProductPrice
from unit_economics.serializers import ProductPriceSerializer


def moysklad_json_token():
    """Получение JSON токена"""
    BASE_URL = 'https://api.moysklad.ru/api/remap/1.2'
    TOKEN = '/security/bfc927afe4d5353ed015687513d1351bc0a56bcb'
    url = f'{BASE_URL}{TOKEN}'

    # Указываем логин и пароль
    username = 'rauhelper@yandex.ru'
    password = 'preprod123'

    # Кодируем логин и пароль в base64 для заголовка Authorization
    auth_str = f'{username}:{password}'
    auth_bytes = auth_str.encode('ascii')
    auth_base64 = base64.b64encode(auth_bytes).decode('ascii')

    payload = {}

    # Создаем заголовки для запроса
    headers = {
        'Authorization': f'Basic {auth_base64}',
        'Content-Type': 'application/json'
    }

    # Выполняем POST запрос
    response = requests.request("POST", url, headers=headers, data=payload)

    if 200 <= response.status_code < 300:
        token = response.json()['access_token']
        return token
    return None


class ProductPriceViewSet(ModelViewSet):
    """ViewSet для работы с продуктами"""
    queryset = ProductPrice.objects.all()
    serializer_class = ProductPriceSerializer

    def list(self, request):
        """Получение данных о продуктах из API и обновление базы данных"""
        # user = request.user
        #
        # try:
        #     account = Account.objects.get(user=user)
        # except Account.DoesNotExist:
        #     return Response({'status': 'error', 'message': 'Account not found for this user'},
        #                     status=status.HTTP_404_NOT_FOUND)
        #
        # auth_token = moysklad_json_token()

        api_url = "https://api.moysklad.ru/api/remap/1.2/entity/assortment?filter=archived=false;type=product,bundle"
        headers = {
            'Authorization': 'bfc927afe4d5353ed015687513d1351bc0a56bcb',
            'Content-Type': 'application/json'
        }
        response = requests.get(api_url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            products = data.get('rows', [])

            for item in products:
                try:
                    # Найти продукт по SKU
                    product = Product.objects.get(sku=item['id'])  # `item['id']` используется как SKU

                    # Создать или обновить запись в ProductPrice
                    ProductPrice.objects.update_or_create(
                        product=product,
                        platform=account.platform,
                        defaults={
                            'price': item.get('salePrices', [{}])[0].get('value', None),
                            'cost_price': item.get('supplier', {}).get('buyPrice', {}).get('value', None),
                        }
                    )

                except Product.DoesNotExist:
                    # Пропустить если продукт с таким SKU не найден
                    continue

            return Response({'status': 'success', 'data': products}, status=status.HTTP_200_OK)
        else:
            return Response({'status': 'error', 'message': response.text}, status=response.status_code)


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
