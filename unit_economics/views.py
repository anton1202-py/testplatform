import logging

import requests
from django.db import transaction
from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from analyticalplatform.settings import (OZON_ID, TOKEN_MY_SKLAD, TOKEN_OZON,
                                         TOKEN_WB, TOKEN_YM)
from core.enums import MarketplaceChoices
from core.models import Account, Platform, User
from unit_economics.integrations import profitability_calculate, save_overheds_for_mp_product
from unit_economics.models import ProductPrice, MarketplaceCommission, MarketplaceProduct
from unit_economics.serializers import ProductPriceSerializer, PlatformSerializer, AccountSerializer, \
    MarketplaceCommissionSerializer, MarketplaceProductSerializer, ProductNameSerializer, BrandSerializer, \
    ProfitabilityMarketplaceProductSerializer
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
        moy_sklad_add_data_to_db()
        wb_products_data_to_db()
        wb_logistic_add_to_db()
        wb_comission_add_to_db()
        ozon_products_data_to_db()
        ozon_comission_logistic_add_data_to_db()
        yandex_add_products_data_to_db()
        yandex_comission_logistic_add_data_to_db()
        profitability_calculate(user_id=user.id)
        updated_products = ProductPrice.objects.all()
        serializer = ProductPriceSerializer(updated_products, many=True)
        return Response(
            {'status': 'success', 'message': f'Total processed: {total_processed}',
             'data': serializer.data},
            status=status.HTTP_200_OK)


class ProductMoySkladViewSet(ModelViewSet):
    # queryset = (ProductPrice.objects.filter(platform=Platform.objects.get(platform_type=MarketplaceChoices.MOY_SKLAD))
    #             .annotate(product_count=Count('id')))
    queryset = (ProductPrice.objects.all()
                .annotate(product_count=Count('id')))
    serializer_class = ProductPriceSerializer


class PlatformViewSet(viewsets.ReadOnlyModelViewSet):
    """Получаем платформы(магазины) текущего пользователя"""
    permission_classes = [IsAuthenticated]
    serializer_class = PlatformSerializer

    def get_queryset(self):
        return Platform.objects.filter(accounts__user=self.request.user).distinct()


class AccountViewSet(viewsets.ReadOnlyModelViewSet):
    """Получаем аккаунты текущего пользователя"""
    permission_classes = [IsAuthenticated]
    serializer_class = AccountSerializer

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user)


class BrandViewSet(viewsets.ViewSet):
    """Получаем бренды товаров текущего пользователя"""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        brands = ProductPrice.objects.filter(mp_product__account__user=self.request.user).values_list('brand',
                                                                                                      flat=True).distinct()
        serializer = BrandSerializer(instance=brands, many=True)
        return Response(serializer.data)


class ProductNameViewSet(viewsets.ViewSet):
    """Получаем название товаров текущего пользователя"""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        product_names = (ProductPrice.objects.filter(mp_product__account__user=self.request.user)
                         .values_list('name', flat=True).distinct())
        serializer = ProductNameSerializer(instance=product_names, many=True)
        return Response(serializer.data)


class MarketplaceProductViewSet(viewsets.ReadOnlyModelViewSet):
    """Получаем товары для выбранной платформы + фильтрация по данным от пользователя"""
    permission_classes = [IsAuthenticated]
    serializer_class = MarketplaceProductSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = MarketplaceProduct.objects.filter(account__user=user)

        platform_id = self.request.query_params.get('platform_id')
        account_id = self.request.query_params.get('account_id')
        brand = self.request.query_params.get('brand')
        product_name = self.request.query_params.get('product_name')
        # Фильтрация по умолчанию по платформе "Wildberries"
        if not platform_id:
            platform_id = 1  # ID платформы "Wildberries"

        if platform_id:
            queryset = queryset.filter(platform_id=platform_id)
        if account_id:
            queryset = queryset.filter(account_id=account_id)
        if brand:
            queryset = queryset.filter(product__brand=brand)
        if product_name:
            queryset = queryset.filter(product__name__icontains=product_name)

        return queryset


class ProfitabilityAPIView(GenericAPIView):
    """
    API для расчета рентабельности и сохранения накладных расходов.
    """
    serializer_class = ProfitabilityMarketplaceProductSerializer

    def get(self, request, *args, **kwargs):
        """
        GET-запрос для расчета рентабельности всех товаров пользователя.
        """
        user_id = self.kwargs.get('user_id')

        try:
            result = profitability_calculate(user_id)
            return Response(result, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, *args, **kwargs):
        """
        POST-запрос для обновления накладных расходов и пересчета рентабельности.
        Входящие данные:
        mp_product_dict: словарь типа {mp_product_id: product_overheads}
        mp_product_id - id продлукта из таблицы MarketplaceProduct
        product_overheads - накладные расходы в формате float (например 0.2)
        """
        overheads_data = request.data.get('overheads_data', {})
        user_id = request.data.get('user_id')

        if not overheads_data or not user_id:
            return Response({"error": "Invalid data"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Сохраняем накладные расходы
            save_overheds_for_mp_product(overheads_data)

            # Пересчитываем рентабельность
            result = profitability_calculate(user_id)

            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

# class MarketplaceCommissionViewSet(viewsets.ReadOnlyModelViewSet):
#     permission_classes = [IsAuthenticated]
#     serializer_class = MarketplaceCommissionSerializer
#
#     def get_queryset(self):
#         # Получаем все комиссии, возможна фильтрация по товару
#         product_id = self.request.query_params.get('product')
#         if product_id:
#             return MarketplaceCommission.objects.filter(marketplace_product__product_id=product_id)
#         return MarketplaceCommission.objects.none()
