import logging

import requests
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
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
from unit_economics.integrations import (
    calculate_mp_price_with_incoming_profitability,
    calculate_mp_price_with_profitability, profitability_calculate,
    save_overheds_for_mp_product, update_price_info_from_user_request)
from unit_economics.models import (MarketplaceAction, MarketplaceCommission,
                                   MarketplaceProduct,
                                   MarketplaceProductInAction,
                                   MarketplaceProductPriceWithProfitability,
                                   ProductPrice,
                                   ProfitabilityMarketplaceProduct)
from unit_economics.periodic_tasks import (action_article_price_to_db,
                                           moy_sklad_costprice_add_to_db)
from unit_economics.serializers import (
    AccountSelectSerializer, AccountSerializer, BrandSerializer,
    MarketplaceActionSerializer, MarketplaceCommissionSerializer,
    MarketplaceProductInActionSerializer,
    MarketplaceProductPriceWithProfitabilitySerializer,
    MarketplaceProductSerializer, PlatformSerializer, ProductNameSerializer,
    ProductPriceSelectSerializer, ProductPriceSerializer,
    ProfitabilityMarketplaceProductSerializer)
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
        moy_sklad_add_data_to_db()
        # wb_products_data_to_db()
        # wb_logistic_add_to_db()
        # wb_comission_add_to_db()
        # ozon_products_data_to_db()
        # ozon_comission_logistic_add_data_to_db()
        # yandex_add_products_data_to_db()
        # yandex_comission_logistic_add_data_to_db()
        print(' ')
        profitability_calculate(user_id=user.id)
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


class TopSelectorsViewSet(GenericAPIView):
    """
    Получаем информацию по выбору для верхних селекторов на странице

    > Магазин
    > Бренд
    > Товар
    > Маркетплейс
    > Фулфилмент

    На выходе получем словарь с данными:
    {
        accounts: [
            {
                "id": "account_id",
                "name": "account_name",
            }
        ],
        platforms: [
            {
                "id": platform_id,
                "name": "platform_name",
                "platform_type": platform_type
            }
        ],
        brands: [
            {
                "brand": "brand_name",
            }
        ],
        goods:[
            {
                "id": product_id,
                "name": "product_name",
                "brand": "brand_name",
                "vendor": "seller_article"
            }
        ]
    }
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PlatformSerializer

    def get(self, request, *args, **kwargs):
        """
        GET-запрос для получения отфильтрованных данных
        """
        user_id = self.request.query_params.get('user_id')
        accounts_data = Account.objects.filter(user__id=user_id)
        platforms_data = Platform.objects.all()
        brands_data = ProductPrice.objects.all().values('brand').distinct()
        goods_data = ProductPrice.objects.filter(account__user__id=user_id)

        top_selection_platform_id = self.request.query_params.get(
            'top_selection_platform_id')
        top_selection_account_id = self.request.query_params.get(
            'top_selection_account_id')
        top_selection_brand = self.request.query_params.get(
            'top_selection_brand')
        top_selection_product_name = self.request.query_params.get(
            'top_selection_product_name')

        # В приоритете верхние фильтры
        if top_selection_platform_id:
            platforms_list = top_selection_platform_id.split(',')
            accounts_data = accounts_data.filter(
                platform__id__in=platforms_list)
            goods_data = goods_data.filter(
                Q(mp_product__platform__id__in=platforms_list)).distinct()

        if top_selection_account_id:
            accounts_list = top_selection_account_id.split(',')
            # accounts_data = accounts_data.filter(id__in=accounts_list)
            goods_data = goods_data.filter(
                Q(mp_product__account__id__in=accounts_list)).distinct()

        if top_selection_brand:
            brands = top_selection_brand.split(',')
            goods_data = goods_data.filter(brand__in=brands)

        if top_selection_product_name:
            products_list = top_selection_product_name.split(',')

        try:

            main_result = {
                "accounts": AccountSelectSerializer(accounts_data, many=True).data,
                "platforms": PlatformSerializer(platforms_data, many=True).data,
                "brands": brands_data,
                "goods": ProductPriceSelectSerializer(goods_data, many=True).data,
            }
            return Response(main_result, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)


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
    # Подключаем поиск и сортировку
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'barcode']  # Поля для поиска
    # Поля для сортировки ['profit', 'profitability']
    ordering_fields = ['mp_profitability__profit',
                       'mp_profitability__profitability']

    def get_queryset(self):
        user = self.request.user
        queryset = MarketplaceProduct.objects.filter(
            account__user=user).select_related('mp_product_profit_price')

        top_selection_platform_id = self.request.query_params.get(
            'top_selection_platform_id')
        top_selection_account_id = self.request.query_params.get(
            'top_selection_account_id')
        top_selection_brand = self.request.query_params.get(
            'top_selection_brand')
        top_selection_product_name = self.request.query_params.get(
            'top_selection_product_name')

        # Повторяющиеся фильтры в верху страницы и вверху таблицы.
        table_platform_id = self.request.query_params.get('table_platform_id')
        table_brand = self.request.query_params.get('table_brand')

        filter_platform_id = ''

        # В приоритете верхние фильтры
        if top_selection_platform_id:
            filter_platform_id = top_selection_platform_id
        elif table_platform_id:
            filter_platform_id = table_platform_id

        if filter_platform_id:
            platforms_list = filter_platform_id.split(',')
            queryset = queryset.filter(platform__id__in=platforms_list)
        if top_selection_account_id:
            accounts_list = top_selection_account_id.split(',')
            queryset = queryset.filter(account__id__in=accounts_list)
        if top_selection_brand:
            brands = top_selection_brand.split(',')
            queryset = queryset.filter(product__brand__in=brands)
        elif table_brand:
            brands = table_brand.split(',')
            queryset = queryset.filter(product__brand__in=brands)

        if top_selection_product_name:
            products_list = top_selection_product_name.split(',')
            queryset = queryset.filter(product__id__in=products_list)

        # Добавляем prefetch_related для акции
        queryset = queryset.prefetch_related(
            Prefetch('product_in_action',
                     queryset=MarketplaceProductInAction.objects.select_related('action'))
        )
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        profitability_group = request.query_params.get('profitability_group')
        if profitability_group:
            result = profitability_calculate(
                request.user.id, profitability_group=profitability_group)
            queryset = queryset.filter(
                id__in=[p.id for p in result['filtered_products']])
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


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

        queryset = ProfitabilityMarketplaceProduct.objects.filter(
            Q(mp_product__account__user__id=user_id))
        product_situations = ProductPrice.objects.filter(
            Q(account__user__id=user_id))

        top_selection_platform_id = self.request.query_params.get(
            'top_selection_platform_id')
        top_selection_account_id = self.request.query_params.get(
            'top_selection_account_id')
        top_selection_brand = self.request.query_params.get(
            'top_selection_brand')
        top_selection_product_name = self.request.query_params.get(
            'top_selection_product_name')

        # Повторяющиеся фильтры в верху страницы и вверху таблицы

        # В приоритете верхние фильтры
        if top_selection_platform_id:
            platforms_list = top_selection_platform_id.split(',')
            queryset = queryset.filter(
                Q(mp_product__platform__id__in=platforms_list))
            product_situations = product_situations.filter(
                Q(mp_product__platform__id__in=platforms_list)).distinct()
        if top_selection_account_id:
            accounts_list = top_selection_account_id.split(',')
            queryset = queryset.filter(
                mp_product__account__id__in=accounts_list)
            product_situations = product_situations.filter(
                Q(mp_product__account__id__in=accounts_list))

        if top_selection_brand:
            brands = top_selection_brand.split(',')
            queryset = queryset.filter(mp_product__product__brand__in=brands)
            product_situations = product_situations.filter(brand__in=brands)

        if top_selection_product_name:
            products_list = top_selection_product_name.split(',')
            queryset = queryset.filter(
                mp_product__product__id__in=products_list)
            product_situations = product_situations.filter(
                id__in=products_list)

        try:
            result = queryset.aggregate(
                count_above_20=Count('id', filter=Q(profitability__gt=20)),
                count_between_10_and_20=Count('id', filter=Q(
                    profitability__lte=20) & Q(profitability__gt=10)),
                count_between_0_and_10=Count('id', filter=Q(
                    profitability__lte=10) & Q(profitability__gt=0)),
                count_between_0_and_minus_10=Count('id', filter=Q(
                    profitability__lte=0) & Q(profitability__gt=-10)),
                count_between_minus_10_and_minus_20=Count('id', filter=Q(
                    profitability__lte=-10) & Q(profitability__gt=-20)),
                count_below_minus_20=Count(
                    'id', filter=Q(profitability__lte=-20)),
            )
            product_situations = len(product_situations)
            main_result = {
                'diagram_data': result,
                'product_situations': product_situations

            }
            return Response(main_result, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, *args, **kwargs):
        """
        POST-запрос для обновления накладных расходов и пересчета рентабельности.
        Входящие данные:
        mp_product_dict: словарь типа {mp_product_id: product_overheads}
        mp_product_id - id продукта из таблицы MarketplaceProduct
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


# class ProfitabilityAPIView(GenericAPIView):
#     """
#     API для расчета рентабельности и сохранения накладных расходов.
#     """
#     serializer_class = ProfitabilityMarketplaceProductSerializer
#
#     def get(self, request, *args, **kwargs):
#         """
#         GET-запрос для расчета рентабельности всех товаров пользователя (данные для графика).
#         """
#         user_id = self.kwargs.get('user_id')
#         category = request.query_params.get('category')
#
#         try:
#             result = profitability_calculate(user_id)
#             if category:
#                 products = result['products_by_profitability'].get(
#                     category, [])
#                 return Response(products, status=status.HTTP_200_OK)
#             else:
#                 return Response(result, status=status.HTTP_200_OK)
#         except User.DoesNotExist:
#             return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
#
#     def post(self, request, *args, **kwargs):
#         """
#         POST-запрос для обновления накладных расходов и пересчета рентабельности.
#         Входящие данные:
#         mp_product_dict: словарь типа {mp_product_id: product_overheads}
#         mp_product_id - id продлукта из таблицы MarketplaceProduct
#         product_overheads - накладные расходы в формате float (например 0.2)
#         """
#         overheads_data = request.data.get('overheads_data', {})
#         user_id = request.data.get('user_id')
#
#         if not overheads_data or not user_id:
#             return Response({"error": "Invalid data"}, status=status.HTTP_400_BAD_REQUEST)
#
#         try:
#             # Сохраняем накладные расходы
#             save_overheds_for_mp_product(overheads_data)
#
#             # Пересчитываем рентабельность
#             result = profitability_calculate(user_id)
#
#             return Response(result, status=status.HTTP_200_OK)
#         except Exception as e:
#             return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# class ProductsByCategoryAPIView(APIView):
#     def get(self, request, user_id):
#         category = request.query_params.get('category')
#         if not category:
#             return Response({"error": "Category parameter is required"}, status=status.HTTP_400_BAD_REQUEST)
#
#         try:
#             user = User.objects.get(id=user_id)
#         except User.DoesNotExist:
#             return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
#
#         filter_conditions = {
#             'above_20': Q(mp_profitability__profitability__gt=20),
#             'between_10_and_20': Q(mp_profitability__profitability__lt=20) & Q(mp_profitability__profitability__gt=10),
#             'between_0_and_10': Q(mp_profitability__profitability__gt=0) & Q(mp_profitability__profitability__lt=10),
#             'between_0_and_minus_10': Q(mp_profitability__profitability__lt=0) & Q(mp_profitability__profitability__gt=-10),
#             'between_minus10_and_minus_20': Q(mp_profitability__profitability__gt=-20) & Q(mp_profitability__profitability__lt=-10),
#             'below_minus_20': Q(mp_profitability__profitability__lt=-20),
#         }
#
#         if category not in filter_conditions:
#             return Response({"error": "Invalid category"}, status=status.HTTP_400_BAD_REQUEST)
#
#         products = MarketplaceProduct.objects.filter(
#             account__user=user
#         ).filter(
#             filter_conditions[category]
#         ).select_related(
#             'product', 'product__price_product', 'marketproduct_comission', 'marketproduct_logistic', 'mp_profitability'
#         )
#
#         serializer = MarketplaceProductSerializer(products, many=True)
#         return Response(serializer.data, status=status.HTTP_200_OK)


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


class MarketplaceActionListView(APIView):
    """На входе надо список id товаров отфильтрованных по селекторам в body
       пример "product_ids": [1977, 617, 618, 4242].
       Дополнительно принимает action_id, что бы отдать данные для выбранной акции
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
            queryset = queryset.filter(platform__id=platform_id)
        # Фильтрация по названию акции, если параметр передан
        action_name = self.request.query_params.get('action_name')
        if action_name:
            queryset = queryset.filter(action_name__icontains=action_name)
        # Сортировка по платформе и названию акции
        queryset = queryset.order_by('platform_id', 'action_name')

        return queryset

    def post(self, request, *args, **kwargs):
        today = timezone.now().date()
        product_ids = request.data.get('product_ids')
        action_id = request.data.get('action_id')

        if not product_ids:
            return Response({"detail": "Нужно id товаров"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product_ids = [int(pid) for pid in product_ids]
        except ValueError:
            return Response({"detail": "Не верный формат"}, status=status.HTTP_400_BAD_REQUEST)

        # Получаем ID акций, содержащих указанные товары
        actions_ids = MarketplaceProductInAction.objects.filter(
            marketplace_product__id__in=product_ids
        ).values_list('action_id', flat=True).distinct()

        # Фильтруем акции, которые еще не закончились и имеют указанные ID
        actions = MarketplaceAction.objects.filter(
            id__in=actions_ids,
            date_finish__gt=today
        ).prefetch_related('account__platform')  # Здесь добавляем правильные связи
        if action_id:
            actions = actions.filter(id=action_id)
        filtered_actions = []
        for action in actions:
            filtered_products = action.action.filter(
                marketplace_product__id__in=product_ids)
            if filtered_products.exists():
                action_data = {
                    'platform': action.platform.id,
                    'account': action.account.id,
                    'action_number': action.action_number,
                    'action_name': action.action_name,
                    'date_start': action.date_start,
                    'date_finish': action.date_finish,
                    'products': MarketplaceProductInActionSerializer(filtered_products, many=True).data
                }
                filtered_actions.append(action_data)

        return Response(filtered_actions)

# class MarketplaceActionListView(ListAPIView):
#     """Все акции и товары в них. Апишка принимает параметр платформы пример - GET /marketplace-actions/?platform=1
#         + параметр название акции action_name и отдаёт отсортированные данные по платформе.
#         /marketplace-actions/?product_ids=1,2,3
#     """
#     serializer_class = MarketplaceActionSerializer
#     permission_classes = [IsAuthenticated]
#
#     def get(self, request, *args, **kwargs):
#         # Получаем текущую дату
#         today = timezone.now().date()
#         # Получаем список ID товаров от фронта
#         product_ids = request.query_params.get('product_ids')
#         if not product_ids:
#             return Response({"detail": "Нужно id товаров"}, status=status.HTTP_400_BAD_REQUEST)
#
#         try:
#             product_ids = list(map(int, product_ids.split(',')))
#         except ValueError:
#             return Response({"detail": "Не верный формат"}, status=status.HTTP_400_BAD_REQUEST)
#
#         # Получаем ID акций, содержащих указанные товары
#         actions_ids = MarketplaceProductInAction.objects.filter(
#             marketplace_product__id__in=product_ids   #,status=True  # Надо ли товары учасвствующие в акции?
#         ).values_list('action_id', flat=True).distinct()
#
#         # Фильтруем акции, которые еще не закончились и имеют указанные ID
#         actions = MarketplaceAction.objects.filter(
#             id__in=actions_ids,
#             date_finish__gt=today
#         )
#
#         # Сериализация и возврат данных
#         serializer = self.serializer_class(actions, many=True)
#         return Response(serializer.data)


class CalculateMPPriceView(APIView):
    """
    Эндпоинт для расчета цены товара на маркетплейсе на основе рентабельности.

    Входящие данные (в теле POST-запроса):
        incoming_profitability: float - входящая рентабельность с которой сравниваем рентабельность из БД
        product_ids: list - список ID товаров, которые находятся на странице

    Возвращает:
        Список объектов модели MarketplaceProduct с обновленными ценами.
    """

    def post(self, request, *args, **kwargs):
        incoming_profitability = request.data.get('incoming_profitability')
        product_ids = request.data.get('product_ids')

        if not incoming_profitability or not product_ids:
            return Response({"detail": "Нужно указать входящую рентабельность и список ID товаров"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product_ids = [int(pid) for pid in product_ids]
        except ValueError:
            return Response({"detail": "Не верный формат ID товаров"}, status=status.HTTP_400_BAD_REQUEST)

        mp_products_list = calculate_mp_price_with_incoming_profitability(
            incoming_profitability, product_ids)

        serializer = MarketplaceProductSerializer(mp_products_list, many=True)
        return Response(serializer.data)


class MarketplaceProductPriceWithProfitabilityViewSet(viewsets.ReadOnlyModelViewSet):
    """    
    profit_price - это по Fifo
    usual_price = простая рентабельность
    """
    permission_classes = [IsAuthenticated]
    serializer_class = MarketplaceProductPriceWithProfitabilitySerializer
    filter_backends = [SearchFilter]
    # Поле для фильтрации по бренду
    search_fields = ['mp_product__product__brand']

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
