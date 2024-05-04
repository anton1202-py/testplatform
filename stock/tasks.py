from analyticalplatform.celery import app
from core.models import Account
from core.utils import skip_if_running


@app.task(bind=True)
@skip_if_running
def periodic_orders_parse(*_):
    accounts = Account.objects.all()

    for account in accounts:
        account.get_platform_orders_processor().refresh_orders()
