from django.db.models import QuerySet

from core.enums import MarketplaceChoices
from core.models import Account


def get_user_accounts(user) -> QuerySet[Account]:
    accounts = Account.objects.filter(user=user).exclude(platform__platform_type=MarketplaceChoices.MOY_SKLAD)

    return accounts
