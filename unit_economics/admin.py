from django.contrib import admin
from unit_economics.models import ProductPrice


@admin.register(ProductPrice)
class ProductPriceAdmin(admin.ModelAdmin):
    """Регистрация в админ панели модели ProductPrice."""

    list_display = ['id', 'account', 'platform', 'name', 'brand', 'sku', 'vendor', 'barcode', 'type', 'price', 'cost_price']   # Поля отображаемые в админке
    list_filter = ['brand', 'type']  # Фильтрации по указанным полям
    search_fields = ['name', 'brand', 'price', 'cost_price']   # Поле поиска по указанным полям
    ordering = ["-id",]   # Упорядочивание по умолчанию
    exclude = ["id",]   # Поля исключены из редактируемых


    # list_display = ['id', 'product', 'platform', 'price', 'cost_price']   # Поля отображаемые в админке
    # list_filter = ["id", 'price', 'cost_price']  # Фильтрации по указанным полям
    # search_fields = ['product', 'platform', 'price', 'cost_price']   # Поле поиска по указанным полям
    # ordering = ["id",]   # Упорядочивание по умолчанию
    # exclude = ["id",]   # Поля исключены из редактируемых