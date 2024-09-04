import logging

from api_requests.ozon_requests import (ozon_products_comission_info_from_api,
                                        ozon_products_info_from_api)
from core.enums import MarketplaceChoices
from core.models import Account, Platform, User
from unit_economics.integrations import (add_marketplace_comission_to_db,
                                         add_marketplace_logistic_to_db,
                                         add_marketplace_product_to_db,
                                         sender_error_to_tg)
from unit_economics.models import MarketplaceProduct

logger = logging.getLogger(__name__)


@sender_error_to_tg
def ozon_price_articles(TOKEN_OZON, OZON_ID):
    """
    Возвращает словарь типа {product_id: price_after_discount}
    """
    data_list = ozon_products_comission_info_from_api(TOKEN_OZON, OZON_ID)
    price_dict = {}
    if data_list:
        for data in data_list:
            price_dict[data['product_id']] = data['price']['price']
    return price_dict


@sender_error_to_tg
def ozon_comission_logistic_add_data_to_db():
    """
    Записывает комиссии и затрат на логистику OZON в базу данных
    """

    users = User.objects.all()
    for user in users:

        accounts_wb = Account.objects.filter(
            user=user,
            platform=Platform.objects.get(
                platform_type=MarketplaceChoices.OZON)
        )
        for account in accounts_wb:
            ozon_token = account.authorization_fields['token']
            ozon_client_id = account.authorization_fields['client_id']
            data_list = ozon_products_comission_info_from_api(
                ozon_token, ozon_client_id)

            for data in data_list:
                try:
                    product_obj = MarketplaceProduct.objects.get(
                        account=account,
                        platform=Platform.objects.get(
                            platform_type=MarketplaceChoices.OZON),
                        sku=data['product_id'])
                    comissions_data = data['commissions']

                    fbs_commission = comissions_data['sales_percent_fbs']
                    fbo_commission = comissions_data['sales_percent_fbo']
                    add_marketplace_comission_to_db(product_obj, fbs_commission,
                                                    fbo_commission)

                    cost_logistic_fbo = comissions_data['fbo_deliv_to_customer_amount'] + \
                        comissions_data['fbo_fulfillment_amount'] + \
                        comissions_data['fbo_direct_flow_trans_max_amount']
                    cost_logistic_fbs = comissions_data['fbs_deliv_to_customer_amount'] + \
                        comissions_data['fbs_direct_flow_trans_max_amount']

                    add_marketplace_logistic_to_db(
                        product_obj, cost_logistic_fbo=cost_logistic_fbo, cost_logistic_fbs=cost_logistic_fbs)
                except MarketplaceProduct.DoesNotExist:
                    logger.info(
                        f'В модели MarketplaceProduct (ОЗОН) нет sku {data["product_id"]}')


@sender_error_to_tg
def ozon_products_data_to_db():
    """Записывает данные о продуктах OZON в базу данных"""
    users = User.objects.all()
    for user in users:
        account_sklad = Account.objects.get(
            user=user,
            platform=Platform.objects.get(
                platform_type=MarketplaceChoices.MOY_SKLAD),
        )
        accounts_ozon = Account.objects.filter(
            user=user,
            platform=Platform.objects.get(
                platform_type=MarketplaceChoices.OZON)
        )
        for account in accounts_ozon:
            ozon_token = account.authorization_fields['token']
            ozon_client_id = account.authorization_fields['client_id']
            main_data = ozon_products_info_from_api(ozon_token, ozon_client_id)
            for data in main_data:
                platform = Platform.objects.get(
                    platform_type=MarketplaceChoices.OZON)
                name = data['name']
                sku = data['id']
                seller_article = data['offer_id']
                barcode = data['barcode']
                category_number = data['description_category_id']
                category_name = ''
                width = data['width']/10
                height = data['height']/10
                length = data['depth']/10
                weight = data['weight']/1000

                add_marketplace_product_to_db(
                    account_sklad, barcode,
                    account, platform, name,
                    sku, seller_article, category_number,
                    category_name, width,
                    height, length, weight)
