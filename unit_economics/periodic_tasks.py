from analyticalplatform.celery import app
from core.models import Account
from unit_economics.models import (MarketplaceAction, ProductCostPrice,
                                   ProductPrice)
from unit_economics.tasks_moy_sklad import (moy_sklad_add_data_to_db,
                                            moy_sklad_costprice_calculate)
from unit_economics.tasks_ozon import (ozon_action_article_price_to_db,
                                       ozon_action_data_to_db,
                                       ozon_comission_logistic_add_data_to_db,
                                       ozon_products_data_to_db)
from unit_economics.tasks_wb import (wb_action_article_price_to_db,
                                     wb_action_data_to_db,
                                     wb_comission_add_to_db,
                                     wb_logistic_add_to_db,
                                     wb_products_data_to_db)
from unit_economics.tasks_yandex import (
    yandex_action_article_price_to_db, yandex_action_data_to_db,
    yandex_add_products_data_to_db, yandex_comission_logistic_add_data_to_db)


@app.task()
def update_moy_sklad_product_list():
    """Обновляет данные о продуктах c Мой Склад"""
    moy_sklad_add_data_to_db()


@app.task()
def update_wildberries_product_list():
    """Обновляет данные о продуктах c Wildberries"""
    wb_products_data_to_db()
    wb_comission_add_to_db()
    wb_logistic_add_to_db()


@app.task()
def update_ozon_product_list():
    """Обновляет данные о продуктах c Ozon"""
    ozon_products_data_to_db()
    ozon_comission_logistic_add_data_to_db()


@app.task()
def update_yandex_product_list():
    """Обновляет данные о продуктах c Yandex"""
    yandex_add_products_data_to_db()
    yandex_comission_logistic_add_data_to_db()


@app.task(time_limit=36000)
def moy_sklad_costprice_add_to_db():
    """
    Записывает себестоимость (методом оприходования) товара в базу данных
    """
    cost_price_data = moy_sklad_costprice_calculate()
    for account, cost_price_list in cost_price_data.items():
        for data in cost_price_list:
            barcodes_list = data['barcodes']
            cost_price = data['cost_price']
            if ProductPrice.objects.filter(
                    account=account, barcode=barcodes_list).exists():
                prod_obj = ProductPrice.objects.filter(
                    account=account, barcode=barcodes_list)
                if len(prod_obj) > 1:
                    print(prod_obj)
                prod_obj = prod_obj[0]
                search_params = {'product': prod_obj}
                values_for_update = {
                    "cost_price": cost_price
                }
                ProductCostPrice.objects.update_or_create(
                    defaults=values_for_update, **search_params
                )


@app.task()
def action_article_price_to_db():
    """
    Записывает возможные цены артикулов из акции
    """
    accounts = Account.objects.all()
    for account in accounts:
        platform = account.platform
        if platform.name == 'Wildberries':
            wb_token = account.authorization_fields['token']
            wb_action_data_to_db()
            actions_data = MarketplaceAction.objects.filter(
                account=account, platform=platform)
            wb_action_article_price_to_db(
                account, actions_data, platform, wb_token)
        if platform.name == 'OZON':
            ozon_action_data_to_db()
            actions_data = MarketplaceAction.objects.filter(
                account=account, platform=platform)
            ozon_action_article_price_to_db(account, actions_data, platform)
        if platform.name == 'Yandex Market':
            yandex_action_data_to_db()
            actions_data = MarketplaceAction.objects.filter(
                account=account, platform=platform)
            yandex_action_article_price_to_db(account, actions_data, platform)
