import enum

from django.db import models


class BaseStatus(models.IntegerChoices):
    NEW = 1, "Новый"
    ACCEPTED = 2, "Принят"
    CONFIRMED_COMPLETE = 3, "Подтвержден-Комплектовать"
    ASSEMBLED_SHIPMENT = 4, "Собран-Отгрузка"
    SHIPPED = 5, "Отгружен"

    CANCELED = 100, "Отменен"
    RETURNED = 101, "Возврат"


class BaseStatusColors(enum.StrEnum):
    DARK_GREEN = "#38783E"
    GREEN = "#00B956"
    YELLOW = "#FFCD1D"
    BROWN = "#CE832B"
    LIGHT_GREEN = "#98C90E"
    GRAY = "#CAC6C6"
    RED = "#FF3041"
