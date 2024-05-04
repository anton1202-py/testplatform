from django.contrib import admin

from core.models import Account, Platform, Product, User


@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ["email", "is_superuser"]


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ["user", "platform", "name"]


@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = [
        "name",
    ]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "name",
    ]
