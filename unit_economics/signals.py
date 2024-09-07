from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from unit_economics.models import MarketplaceCommission, MarketplaceLogistic


# Шаг 3: Создайте обработчик сигнала
@receiver(post_save, sender=MarketplaceCommission)
def logistic_update(sender, instance, created, **kwargs):
    if created:
        print(f'Создана новая запись: {instance.marketplace_product}')
    else:
        print(f'Обновлена запись: {instance.marketplace_product}')
