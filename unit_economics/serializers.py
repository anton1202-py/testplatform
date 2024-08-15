from rest_framework import serializers

from core.serializers import AccountsListSerializers
from unit_economics.models import ProductPrice


class ProductPriceSerializer(serializers.ModelSerializer):
    account = AccountsListSerializers

    class Meta:
        model = ProductPrice
        fields = ['name', 'account', 'platform', 'brand', 'sku', 'vendor', 'barcode', 'type', 'price', 'cost_price']
