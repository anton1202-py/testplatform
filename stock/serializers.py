from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer, Serializer, IntegerField

from stock.models import OrderItem


class OrderItemSerializer(ModelSerializer):

    order_number = SerializerMethodField()
    order_status_name = SerializerMethodField()
    order_status_color = SerializerMethodField()
    platform_name = SerializerMethodField()
    product_name = SerializerMethodField()
    product_brand = SerializerMethodField()
    product_barcode = SerializerMethodField()
    created_dt = SerializerMethodField()
    shipped_dt = SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "product",
            "quantity",
            "price",
            "sticker",
            "order_number",
            "order_status_name",
            "order_status_color",
            "platform_name",
            "product_name",
            "product_brand",
            "product_barcode",
            "created_dt",
            "shipped_dt",
        )

    def get_order_number(self, obj):
        if hasattr(obj, "order_number"):
            return obj.order_number
        return "-"

    def get_order_status_name(self, obj):
        if hasattr(obj, "order_status_name"):
            return obj.order_status_name
        return "-"

    def get_order_status_color(self, obj):
        if hasattr(obj, "order_status_color"):
            return obj.order_status_color
        return "-"

    def get_platform_name(self, obj):
        if hasattr(obj, "platform_name"):
            return obj.platform_name
        return "-"

    def get_product_name(self, obj):
        if hasattr(obj, "product_name"):
            return obj.product_name
        return "-"

    def get_product_brand(self, obj):
        if hasattr(obj, "product_brand"):
            return obj.product_brand
        return "-"

    def get_product_barcode(self, obj):
        if hasattr(obj, "product_barcode"):
            return obj.product_barcode
        return "-"

    def get_created_dt(self, obj):
        if hasattr(obj, "created_dt"):
            return obj.created_dt
        return "-"

    def get_shipped_dt(self, obj):
        if hasattr(obj, "product_barcode"):
            return obj.shipped_dt
        return "-"
