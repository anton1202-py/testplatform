from django.utils import timezone
from rest_framework import serializers

from core.models import Account, Platform
from core.serializers import AccountsListSerializers
from unit_economics.models import (MarketplaceAction, MarketplaceCommission,
                                   MarketplaceProduct,
                                   MarketplaceProductInAction,
                                   MarketplaceProductPriceWithProfitability,
                                   ProductPrice,
                                   ProfitabilityMarketplaceProduct)


class PlatformSerializer(serializers.ModelSerializer):
    class Meta:
        model = Platform
        fields = ['id', 'name', 'platform_type']


class AccountSerializer(serializers.ModelSerializer):
    platform = PlatformSerializer()

    class Meta:
        model = Account
        fields = ['id', 'name', 'platform']


class AccountSelectSerializer(serializers.ModelSerializer):

    class Meta:
        model = Account
        fields = ['id', 'name']


class BrandSerializer(serializers.Serializer):
    brand = serializers.CharField()


class ProductNameSerializer(serializers.Serializer):
    name = serializers.CharField()


class ProductPriceSelectSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductPrice
        fields = ['id', 'name', 'brand', 'vendor']


class MarketplaceProductSerializer(serializers.ModelSerializer):
    brand = serializers.CharField(source='product.brand', read_only=True)
    cost_price = serializers.FloatField(
        source='product.cost_price', read_only=True)

    posting_costprice = serializers.FloatField(
        source='product.costprice_product.cost_price', read_only=True)
    rrc = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    commission = serializers.SerializerMethodField()
    logistic_cost = serializers.SerializerMethodField()
    overheads = serializers.FloatField(
        source='mp_profitability.overheads', read_only=True)
    profit = serializers.FloatField(
        source='mp_profitability.profit', read_only=True)
    profitability = serializers.FloatField(
        source='mp_profitability.profitability', read_only=True)
    image = serializers.SerializerMethodField()
    profit_price = serializers.FloatField(
        source='mp_product_profit_price.profit_price', read_only=True)
    usual_price = serializers.FloatField(
        source='mp_product_profit_price.usual_price', read_only=True)
    actions = serializers.SerializerMethodField()

    class Meta:
        model = MarketplaceProduct
        fields = [
            'id', 'name', 'sku', 'seller_article', 'barcode', 'brand', 'cost_price', 'posting_costprice', 'rrc', 'price', 'commission',
            'logistic_cost', 'overheads', 'profit', 'profitability', 'image', 'profit_price', 'usual_price', 'actions', 'change_price_flag'
        ]

    def get_rrc(self, obj):
        return obj.product.price_product.rrc

    def get_price(self, obj):
        platform_name = obj.platform.name.lower()
        if platform_name == 'wildberries':
            return obj.product.price_product.wb_price
        elif platform_name == 'yandex market':
            return obj.product.price_product.yandex_price
        elif platform_name == 'ozon':
            ozon_price = obj.product.ozon_price_product.filter(
                account=obj.account).first()
            return ozon_price.ozon_price if ozon_price else None
        return None

    def get_commission(self, obj):
        try:
            commission = obj.marketproduct_comission
            if commission:
                return {
                    'fbs_commission': commission.fbs_commission,
                    'fbo_commission': commission.fbo_commission,
                    'dbs_commission': commission.dbs_commission,
                    'fbs_express_commission': commission.fbs_express_commission
                }
            return {}
        except MarketplaceProduct.marketproduct_comission.RelatedObjectDoesNotExist:
            return {}

    def get_logistic_cost(self, obj):
        try:
            logistic = obj.marketproduct_logistic
            if logistic:
                return {
                    'cost_logistic': logistic.cost_logistic,
                    'cost_logistic_fbo': logistic.cost_logistic_fbo,
                    'cost_logistic_fbs': logistic.cost_logistic_fbs
                }
            return {}
        except MarketplaceProduct.marketproduct_logistic.RelatedObjectDoesNotExist:
            return {}

    # def get_posting_costprice(self, obj):
    #     if obj.product.costprice_product.cost_price:
    #         return obj.product.costprice_product.cost_price
    #     return None

    def get_image(self, obj):
        if obj.product.image:
            return obj.product.image.url
        return None

    def get_actions(self, obj):
        # Получаем только активные акции
        print('obj', obj)
        MarketplaceProductInAction.objects.filter(marketplace_product=obj)
        product_in_actions = obj.product_in_action.filter(action__date_finish__gte=timezone.now().date(), status=True)
        print('product_in_actions', product_in_actions)
        return MarketplaceProductInActionSerializer(product_in_actions, many=True).data


class MarketplaceCommissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketplaceCommission
        fields = ['fbs_commission', 'fbo_commission',
                  'dbs_commission', 'fbs_express_commission']


class ProductPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductPrice
        fields = ['id', 'account', 'moy_sklad_product_number', 'name', 'brand', 'vendor', 'barcode', 'product_type',
                  'cost_price', 'image',]


class ProfitabilityMarketplaceProductSerializer(serializers.ModelSerializer):
    product = ProductPriceSerializer()

    class Meta:
        model = ProfitabilityMarketplaceProduct
        fields = ['product', 'profit', 'profitability', 'overheads']


class MarketplaceActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketplaceAction
        fields = ['id', 'action_number', 'action_name', 'date_start', 'date_finish']


class MarketplaceProductInActionSerializer(serializers.ModelSerializer):
    action = MarketplaceActionSerializer()

    class Meta:
        model = MarketplaceProductInAction
        fields = ['action', 'product_price', 'status']


# class MarketplaceProductInActionSerializer(serializers.ModelSerializer):
#
#     class Meta:
#         model = MarketplaceProductInAction
#         fields = ['marketplace_product', 'action', 'product_price', 'status']
#
#
# class MarketplaceActionSerializer(serializers.ModelSerializer):
#     products = MarketplaceProductInActionSerializer(
#         many=True, source='action')  # Используем source для связи
#     platform = PlatformSerializer()
#     account = AccountSerializer()
#
#     class Meta:
#         model = MarketplaceAction
#         fields = ['platform', 'account', 'action_number',
#                   'action_name', 'date_start', 'date_finish', 'products']


class MarketplaceProductPriceWithProfitabilitySerializer(serializers.ModelSerializer):
    # Получаем id связанной модели MarketplaceProduct
    id = serializers.IntegerField(source='mp_product.id', read_only=True)
    # Получаем бренд продукта через связь с MarketplaceProduct
    brand = serializers.CharField(
        source='mp_product.product.brand', read_only=True)
    # Поля для цены
    profit_price = serializers.FloatField(read_only=True)
    usual_price = serializers.FloatField(read_only=True)

    class Meta:
        model = MarketplaceProductPriceWithProfitability
        fields = ['id', 'brand', 'profit_price', 'usual_price']
