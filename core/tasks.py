from analyticalplatform.celery import app
from core.models import Account
from core.utils import skip_if_running
from stock.tasks import periodic_orders_parse


@app.task(bind=True)
@skip_if_running
def periodic_products_parse(*_):
    accounts = Account.objects.all()

    users = []

    for account in accounts:
        if account.user not in users:
            users.append(account.user)
        account.get_platform_processor().refresh_products()

    for user in users:
        user.refresh_user_products_connections()

    periodic_orders_parse.apply_async()
