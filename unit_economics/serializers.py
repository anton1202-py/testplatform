from rest_framework import serializers

from unit_economics.models import ProductPrice


class ProductPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductPrice
        fields = ['id', 'product', 'platform', 'price', 'cost_price']
