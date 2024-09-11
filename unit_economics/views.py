import logging

import requests
from django.db import transaction
from django.utils import timezone
from django.db.models import Count, Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from analyticalplatform.settings import (OZON_ID, TOKEN_MY_SKLAD, TOKEN_OZON,
                                         TOKEN_WB, TOKEN_YM)
from api_requests.moy_sklad import change_product_price
from core.enums import MarketplaceChoices
from core.models import Account, Platform, User
from unit_economics.integrations import (profitability_calculate,
                                         save_overheds_for_mp_product, update_price_info_from_user_request,
                                         calculate_mp_price_with_profitability)
from unit_economics.models import (MarketplaceCommission, MarketplaceProduct,
                                   ProductPrice, MarketplaceAction, MarketplaceProductPriceWithProfitability)
from unit_economics.periodic_tasks import (action_article_price_to_db,
                                           moy_sklad_costprice_add_to_db)
from unit_economics.serializers import (
    AccountSerializer, BrandSerializer, MarketplaceCommissionSerializer,
    MarketplaceProductSerializer, PlatformSerializer, ProductNameSerializer,
    ProductPriceSerializer, ProfitabilityMarketplaceProductSerializer, MarketplaceActionSerializer,
    MarketplaceProductPriceWithProfitabilitySerializer)
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
        # change_product_price(TOKEN_MY_SKLAD)
        # moy_sklad_add_data_to_db()
        # wb_products_data_to_db()
        # wb_logistic_add_to_db()
        # wb_comission_add_to_db()
        # ozon_products_data_to_db()
        # ozon_comission_logistic_add_data_to_db()
        # yandex_add_products_data_to_db()
        # yandex_comission_logistic_add_data_to_db()
        # profitability_calculate(user_id=user.id)
        moy_sklad_costprice_add_to_db()
        calculate_mp_price_with_profitability(user.id)
        action_article_price_to_db()
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
    """Получаем товары для выбранной платформы + фильтрация по данным от пользователя
       + поля для поиска 'name', 'barcode' пример запроса GET /api/marketplace-products/?search=123456789
       + поля для сортировки 'profit', 'profitability' пример запроса
       GET /api/marketplace-products/?ordering=mp_profitability__profit
       (или -profit для сортировки по убыванию)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = MarketplaceProductSerializer
    filter_backends = [SearchFilter, OrderingFilter]  # Подключаем поиск и сортировку
    search_fields = ['name', 'barcode']  # Поля для поиска
    ordering_fields = ['mp_profitability__profit', 'mp_profitability__profitability']  # Поля для сортировки ['profit', 'profitability']

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
        GET-запрос для расчета рентабельности всех товаров пользователя (данные для графика).
        """
        user_id = self.kwargs.get('user_id')
        category = request.query_params.get('category')

        try:
            result = profitability_calculate(user_id)
            if category:
                products = result['products_by_profitability'].get(category, [])
                return Response(products, status=status.HTTP_200_OK)
            else:
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


class ProductsByCategoryAPIView(APIView):
    def get(self, request, user_id):
        category = request.query_params.get('category')
        if not category:
            return Response({"error": "Category parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        filter_conditions = {
            'above_20': Q(mp_profitability__profitability__gt=20),
            'between_10_and_20': Q(mp_profitability__profitability__lt=20) & Q(mp_profitability__profitability__gt=10),
            'between_0_and_10': Q(mp_profitability__profitability__gt=0) & Q(mp_profitability__profitability__lt=10),
            'between_0_and_minus_10': Q(mp_profitability__profitability__lt=0) & Q(mp_profitability__profitability__gt=-10),
            'between_minus10_and_minus_20': Q(mp_profitability__profitability__gt=-20) & Q(mp_profitability__profitability__lt=-10),
            'below_minus_20': Q(mp_profitability__profitability__lt=-20),
        }

        if category not in filter_conditions:
            return Response({"error": "Invalid category"}, status=status.HTTP_400_BAD_REQUEST)

        products = MarketplaceProduct.objects.filter(
            account__user=user
        ).filter(
            filter_conditions[category]
        ).select_related(
            'product', 'product__price_product', 'marketproduct_comission', 'marketproduct_logistic', 'mp_profitability'
        )

        serializer = MarketplaceProductSerializer(products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UpdatePriceView(GenericAPIView):
    """
    Представление для обновления цен на товары и накладных расходов.
    Обновляет цены на Мой склад и в БД, если пользователь отправил запрос
    {
        'user_id': user_id.
        'account_id': account_id,
        'platform_name': platform_name,
        'products_data': [
            {
                'marketplaceproduct_id': marketplaceproduct_id,
                'new_price': new_price,
                'overhead': overhead
            }
        ]
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            # Вызов вашей функции для обновления цен
            update_price_info_from_user_request(request.data)
            return Response({"detail": "Цены успешно обновлены"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CalculateMarketplacePriceView(GenericAPIView):
    """
    Вычисление цены на маркетплейсе на основе рентабельности
    в body нужно прокинуть user_id пользователя.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user_id = request.user.id
        calculate_mp_price_with_profitability(user_id)
        return Response({"detail": "Цены успешно обновлены."})


class MarketplaceActionListView(ListAPIView):
    """Все акции и товары в них. Апишка принимает параметр платформы пример - GET /marketplace-actions/?platform=1
        + параметр название акции action_name и отдаёт отсортированные данные по платформе.
    """
    serializer_class = MarketplaceActionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Получаем текущую дату
        today = timezone.now().date()
        # Фильтруем акции, которые еще не закончились
        queryset = MarketplaceAction.objects.filter(date_finish__gt=today)
        # Фильтрация по платформе, если параметр передан
        platform_id = self.request.query_params.get('platform')
        if platform_id:
            queryset = queryset.filter(platform_id=platform_id)
        # Фильтрация по названию акции, если параметр передан
        action_name = self.request.query_params.get('action_name')
        if action_name:
            queryset = queryset.filter(action_name__icontains=action_name)
        # Сортировка по платформе и названию акции
        queryset = queryset.order_by('platform_id', 'action_name')

        return queryset


class MarketplaceProductPriceWithProfitabilityViewSet(viewsets.ReadOnlyModelViewSet):
    """    profit_price - это по Fifo
           usual_price = простая рентабельность"""
    permission_classes = [IsAuthenticated]
    serializer_class = MarketplaceProductPriceWithProfitabilitySerializer
    filter_backends = [SearchFilter]
    search_fields = ['mp_product__product__brand']  # Поле для фильтрации по бренду

    def get_queryset(self):
        queryset = MarketplaceProductPriceWithProfitability.objects.all()

        # Фильтрация по бренду, если передан параметр 'brand'
        brand = self.request.query_params.get('brand')
        if brand:
            queryset = queryset.filter(mp_product__product__brand=brand)

        return queryset


class UserIdView(APIView):
    """Апишка, которая отдаёт фронту id юзера"""
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        user_id = request.user.id
        return Response({'user_id': user_id})

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
