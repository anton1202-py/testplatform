import logging
from datetime import datetime
import math

from api_requests.ozon_requests import (ozon_actions_list,
                                        ozon_actions_product_price_info,
                                        ozon_product_info_with_sku_data,
                                        ozon_products_comission_info_from_api,
                                        ozon_products_info_from_api)
from core.enums import MarketplaceChoices
from core.models import Account, Platform, User
from unit_economics.integrations import (add_marketplace_comission_to_db,
                                         add_marketplace_logistic_to_db,
                                         add_marketplace_product_to_db, sender_error_to_tg)
from unit_economics.models import (MarketplaceAction, MarketplaceCommission, MarketplaceLogistic, MarketplaceProduct,
                                   MarketplaceProductInAction,
                                   ProductOzonPrice, ProductPrice)


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
        accounts_oz = Account.objects.filter(
            user=user,
            platform=Platform.objects.get(
                platform_type=MarketplaceChoices.OZON)
        )
        for account in accounts_oz:
            ozon_token = account.authorization_fields['token']
            ozon_client_id = account.authorization_fields['client_id']
            data_list = ozon_products_comission_info_from_api(
                ozon_token, ozon_client_id)

            for data in data_list:
                try:
                    if MarketplaceProduct.objects.filter(
                            account=account,
                            platform=Platform.objects.get(
                                platform_type=MarketplaceChoices.OZON),
                            sku=data['product_id']).exists():
                        product_obj = MarketplaceProduct.objects.filter(
                            account=account,
                            platform=Platform.objects.get(
                                platform_type=MarketplaceChoices.OZON),
                            sku=data['product_id'])[0]

                        comissions_data = data['commissions']
                        fbs_commission = comissions_data['sales_percent_fbs']
                        fbo_commission = comissions_data['sales_percent_fbo']
                        add_marketplace_comission_to_db(product_obj, fbs_commission,
                                                        fbo_commission)
                        width = product_obj.width
                        height = product_obj.height
                        lenght = product_obj.length
                        volume_cost_fbo = 0
                        volume_cost_fbs = 0
                        volume = (width * height * lenght) / 1000
                        if volume < 1:
                            volume_cost_fbs = 76
                            volume_cost_fbo = 63
                        elif volume > 190:
                            volume_cost_fbs = 2344
                            volume_cost_fbo = 1953
                        else:
                            volume_cost_fbs = 76 + 12 * math.ceil(volume - 1)
                            volume_cost_fbo = 63 + 10 * math.ceil(volume - 1)
                        cost_logistic_fbo = comissions_data['fbo_deliv_to_customer_amount'] + \
                            comissions_data['fbo_fulfillment_amount'] + \
                            volume_cost_fbo
                        cost_logistic_fbs = comissions_data['fbs_deliv_to_customer_amount'] + \
                            comissions_data['fbs_first_mile_max_amount'] + volume_cost_fbs
                        add_marketplace_logistic_to_db(
                            product_obj, cost_logistic_fbo=cost_logistic_fbo, cost_logistic_fbs=cost_logistic_fbs)
                        # print(f'Сохранил комиссию для {product_obj}')
                except MarketplaceProduct.DoesNotExist:
                    print(f'В модели MarketplaceProduct (ОЗОН) нет sku {data["product_id"]}')
                    logger.info(
                        f'В модели MarketplaceProduct (ОЗОН) нет sku {data["product_id"]}')


@sender_error_to_tg
def ozon_products_data_to_db():
    """Записывает данные о продуктах OZON в базу данных"""
    users = User.objects.all()
    platform = Platform.objects.get(
        platform_type=MarketplaceChoices.OZON)
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
                platform=platform
            )
            for account in accounts_ozon:
                ozon_token = ''
                ozon_client_id = ''
                ozon_token = account.authorization_fields['token']
                ozon_client_id = account.authorization_fields['client_id']
                main_data = ozon_products_info_from_api(
                    ozon_token, ozon_client_id)
                print('len(main_data) ozon_products_data_to_db', len(main_data))
                # Получаем все товары для данного аккаунта
                existing_products = MarketplaceProduct.objects.filter(account=account)
                # Создаем множество SKU из API
                api_skus = {data['id'] for data in main_data}
                # Обновляем флаг is_active для существующих товаров
                for product in existing_products:
                    if int(product.sku) in api_skus:
                        product.is_active = True
                        api_skus.remove(int(product.sku))
                    else:
                        product.is_active = False
                    product.save()
                for data in main_data:
                    ozonsku = ''
                    sku = ''
                    barcode = ''
                    article_info = ozon_product_info_with_sku_data(
                        ozon_token, ozon_client_id, data['id'])
                    if article_info:
                        ozonsku = article_info.get('sku', '')
                        if not ozonsku:
                            ozonsku = article_info.get('fbo_sku', '')
                        if not ozonsku:
                            ozonsku = article_info.get('fbs_sku', '')

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
                        height, length, weight, ozonsku)


@sender_error_to_tg
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


@sender_error_to_tg
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
                    marketplace_product = MarketplaceProduct.objects.filter(
                        account=account, sku=nom_id)[0]
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
