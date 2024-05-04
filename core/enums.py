from django.db import models


class MarketplaceChoices(models.IntegerChoices):
    WILDBERRIES = 0, 'Wildberries'
    YANDEX_MARKET = 1, 'Яндекс Маркет'
    MEGA_MARKET = 2, 'МегаМаркет'
    OZON = 3, 'OZON'
    MOY_SKLAD = 4, 'Мой склад'


class FieldsTypes(models.TextChoices):
    NUMBER = "number", "Число"
    TEXT = "text", "Текст"
    PASSWORD = "password", "Пароль"
