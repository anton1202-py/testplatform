from django.db import models


class Status(models.Model):
    """Статус заказа на маркетплейсе."""

    name = models.CharField(max_length=255, verbose_name="Имя статуса из маркетплейса")
    color = models.CharField(max_length=7, verbose_name="Хекс код цвета вместе с #")

    status_code = models.IntegerField(verbose_name="Целочисленный код статуса")

    is_deletable = models.BooleanField(default=True, verbose_name="Можно удалить")

    position = models.PositiveSmallIntegerField(verbose_name="Позиция в линейке статусов")

    my_stock_status_name = models.CharField(max_length=255, verbose_name="Наименование статуса в 'Мой Склад'")

    def __str__(self):
        return f"{self.name}: {self.status_code}"

    class Meta:
        verbose_name = "Статус заказа на маркетплейсе"
        verbose_name_plural = "Статусы заказов на маркетплейсах"


class Order(models.Model):
    """Заказ на маркетплейсе."""

    account = models.ForeignKey(
        "core.Account",
        on_delete=models.CASCADE,
        related_name="orders",
        verbose_name="Аккаунт, к которому относится заказ",
    )
    status = models.ForeignKey(
        Status,
        on_delete=models.PROTECT,
        verbose_name="Статус заказа",
        related_name="orders",
    )

    number = models.CharField(max_length=255, verbose_name="Номер заказа")

    created_dt = models.DateField(verbose_name="Дата и время создания")
    shipped_dt = models.DateField(verbose_name="Дата и время отгрузки", null=True)

    total_price = models.DecimalField(verbose_name="Сумма всего заказа", decimal_places=2, max_digits=10)

    def __str__(self):
        return f"{self.number}"

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"


class OrderItem(models.Model):
    product = models.ForeignKey("core.Product", related_name="order_items", on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=False, blank=False, related_name="items")

    quantity = models.PositiveIntegerField(null=False, blank=False, verbose_name="Количество", default=1)
    price = models.DecimalField(verbose_name="Цена позиции", decimal_places=2, max_digits=10)
    sticker = models.TextField(verbose_name="Base64 представление стикера, получаемого по API", default="")

    is_express = models.BooleanField(default=False, verbose_name="Срочное?")

    def __str__(self):
        return f"{self.product}"

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказов"
