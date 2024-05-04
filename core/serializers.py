from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import ModelSerializer, Serializer, IntegerField

from core.models import Account, Product, Platform


class AccountsListSerializers(ModelSerializer):
    class Meta:
        model = Account
        fields = [
            "id",
            "name",
        ]


class ProductsListSerializers(ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "sku",
            "vendor",
            "barcode"
        ]


class ProductsExportSerializer(Serializer):
    products = serializers.ListField(child=serializers.IntegerField())


class AccountCreateSerializer(ModelSerializer):
    platform_type = IntegerField()

    class Meta:
        model = Account
        fields = [
            "name",
            "platform_type",
            "authorization_fields"
        ]


class ProductManualConnectionCreationSerializer(Serializer):
    other_marketplace_product = IntegerField()
    moy_sklad_product = IntegerField()

    def validate_other_marketplace_product(self, other_marketplace_product):
        if not Product.objects.filter(id=other_marketplace_product).exists():
            raise ValidationError("No other_marketplace_product with given id")
        return other_marketplace_product

    def validate_moy_sklad_product(self, moy_sklad_product):
        if not Product.objects.filter(id=moy_sklad_product).exists():
            raise ValidationError("No moy_sklad_product with given id")
        return moy_sklad_product

    def validate(self, attrs):
        other_marketplace_product = attrs["other_marketplace_product"]
        moy_sklad_product = attrs["moy_sklad_product"]
        if other_marketplace_product == moy_sklad_product:
            return ValidationError("Продукт не может быть в связи с самим собой")
        return attrs
