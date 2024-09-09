import logging
from datetime import datetime

from api_requests.ozon_requests import (ozon_actions_list,
                                        ozon_actions_product_price_info,
                                        ozon_products_comission_info_from_api,
                                        ozon_products_info_from_api)
from core.enums import MarketplaceChoices
from core.models import Account, Platform, User
from unit_economics.integrations import (add_marketplace_comission_to_db,
                                         add_marketplace_logistic_to_db,
                                         add_marketplace_product_to_db)
from unit_economics.models import (MarketplaceAction, MarketplaceProduct,
                                   MarketplaceProductInAction)

                                        #  sender_error_to_tg)

logger = logging.getLogger(__name__)


# @sender_error_to_tg
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


# @sender_error_to_tg
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


# @sender_error_to_tg
def ozon_products_data_to_db():
    """Записывает данные о продуктах OZON в базу данных"""
    users = User.objects.all()
    for user in users:
        if Account.objects.filter(
            user=user,
            platform=Platform.objects.get(
                platform_type=MarketplaceChoices.MOY_SKLAD),
        ).exists():
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

# @sender_error_to_tg


def ozon_action_data_to_db():
    """
    Записывает данные акций OZON в базу данных.
    """
    accounts_ozon = Account.objects.filter(
        platform=Platform.objects.get(
            platform_type=MarketplaceChoices.OZON)
    )
    for account in accounts_ozon:
        oz_token = account.authorization_fields['token']
        ozon_client_id = account.authorization_fields['client_id']
        actions_data = ozon_actions_list(oz_token, ozon_client_id)
        for action in actions_data:
            platform = account.platform
            action_number = action['id']
            action_name = action['title']
            date_start = datetime.strptime(
                action['date_start'], "%Y-%m-%dT%H:%M:%SZ")
            date_finish = datetime.strptime(
                action['date_end'], "%Y-%m-%dT%H:%M:%SZ")

            search_params = {'platform': platform,
                             'account': account, 'action_number': action_number}
            values_for_update = {
                "action_name": action_name,
                "date_start": date_start,
                "date_finish": date_finish
            }
            MarketplaceAction.objects.update_or_create(
                defaults=values_for_update, **search_params)


def ozon_action_article_price_to_db(account, actions_data, platform):
    """
    Записывает возможные цены артикулов OZON из акции
    """

    for data in actions_data:
        oz_token = account.authorization_fields['token']
        ozon_client_id = account.authorization_fields['client_id']
        action_data = ozon_actions_product_price_info(
            oz_token, ozon_client_id, data.action_number)
        if action_data:
            for action_oz in action_data:
                nom_id = action_oz['id']
                if MarketplaceProduct.objects.filter(
                        account=account, sku=nom_id).exists():
                    marketplace_product = MarketplaceProduct.objects.get(
                        account=account, sku=nom_id)
                    action = data
                    product_price = action_oz['max_action_price']
                    if action_oz['action_price'] != 0:
                        status = True
                    else:
                        status = False
                    search_params = {'action': action,
                                     'marketplace_product': marketplace_product}
                    values_for_update = {
                        "product_price": product_price,
                        "status": status
                    }
                    MarketplaceProductInAction.objects.update_or_create(
                        defaults=values_for_update, **search_params)
