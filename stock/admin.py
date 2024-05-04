from django.contrib import admin

from stock.forms import StatusForm
from stock.models import (
    Status,
    Order,
    OrderItem
)


@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    form = StatusForm

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ["status_code"]

        return []

    def has_delete_permission(self, request, obj=None):
        if obj and obj.is_deleted:
            return True

        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["account", "status"]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ["product", "price"]
