from analyticalplatform.celery import app
from unit_economics.tasks_moy_sklad import moy_sklad_add_data_to_db
from unit_economics.tasks_ozon import (ozon_comission_logistic_add_data_to_db,
                                       ozon_products_data_to_db)
from unit_economics.tasks_wb import (wb_comission_add_to_db,
                                     wb_logistic_add_to_db,
                                     wb_products_data_to_db)
from unit_economics.tasks_yandex import (
    yandex_add_products_data_to_db, yandex_comission_logistic_add_data_to_db)


@app.task(bind=True)
def update_moy_sklad_product_list():
    """Обновляет данные о продуктах c Мой Склад"""
    moy_sklad_add_data_to_db()


@app.task(bind=True)
def update_wildberries_product_list():
    """Обновляет данные о продуктах c Wildberries"""
    wb_products_data_to_db()
    wb_comission_add_to_db()
    wb_logistic_add_to_db()


@app.task(bind=True)
def update_ozon_product_list():
    """Обновляет данные о продуктах c Ozon"""
    ozon_products_data_to_db()
    ozon_comission_logistic_add_data_to_db()


@app.task(bind=True)
def update_yandex_product_list():
    """Обновляет данные о продуктах c Yandex"""
    yandex_add_products_data_to_db()
    yandex_comission_logistic_add_data_to_db()
