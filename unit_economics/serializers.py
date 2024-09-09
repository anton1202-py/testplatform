from rest_framework import serializers

from core.models import Account, Platform
from core.serializers import AccountsListSerializers
from unit_economics.models import (MarketplaceCommission, MarketplaceProduct,
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


class BrandSerializer(serializers.Serializer):
    brand = serializers.CharField()


class ProductNameSerializer(serializers.Serializer):
    name = serializers.CharField()


class ProductPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductPrice
        fields = ['id', 'name', 'brand', 'vendor', 'barcode',
                  'product_type', 'cost_price']


class MarketplaceProductSerializer(serializers.ModelSerializer):
    brand = serializers.CharField(source='product.brand', read_only=True)
    cost_price = serializers.FloatField(
        source='product.cost_price', read_only=True)
    rrc = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    commission = serializers.SerializerMethodField()
    logistic_cost = serializers.SerializerMethodField()
    overheads = serializers.FloatField(
        source='mp_profitability.overheads', read_only=True)

    class Meta:
        model = MarketplaceProduct
        fields = [
            'id', 'name', 'sku', 'seller_article', 'barcode',
            'brand', 'cost_price', 'rrc', 'price', 'commission', 'logistic_cost', 'overheads'
        ]

    def get_rrc(self, obj):
        return obj.product.price_product.rrc

    def get_price(self, obj):
        platform_name = obj.platform.name.lower()
        if platform_name == 'wildberries':
            return obj.product.price_product.wb_price
        elif platform_name == 'yandex':
            return obj.product.price_product.yandex_price
        elif platform_name == 'ozon':
            ozon_price = obj.product.ozon_price_product.filter(
                account=obj.account).first()
            return ozon_price.ozon_price if ozon_price else None
        return None

    def get_commission(self, obj):
        commission = obj.marketproduct_comission
        if commission:
            return {
                'fbs_commission': commission.fbs_commission,
                'fbo_commission': commission.fbo_commission,
                'dbs_commission': commission.dbs_commission,
                'fbs_express_commission': commission.fbs_express_commission
            }
        return {}

    def get_logistic_cost(self, obj):
        logistic = obj.marketproduct_logistic
        if logistic:
            return {
                'cost_logistic': logistic.cost_logistic,
                'cost_logistic_fbo': logistic.cost_logistic_fbo,
                'cost_logistic_fbs': logistic.cost_logistic_fbs
            }
        return {}


class MarketplaceCommissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketplaceCommission
        fields = ['fbs_commission', 'fbo_commission',
                  'dbs_commission', 'fbs_express_commission']


class ProfitabilityMarketplaceProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfitabilityMarketplaceProduct
        fields = ['mp_product', 'profit', 'profitability', 'overheads']
