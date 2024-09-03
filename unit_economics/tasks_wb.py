import logging

from api_requests.wb_requests import (wb_article_data_from_api, wb_comissions,
                                      wb_logistic, wb_price_data_from_api)
from core.enums import MarketplaceChoices
from core.models import Account, Platform, User
from unit_economics.integrations import (add_marketplace_comission_to_db,
                                         add_marketplace_logistic_to_db,
                                         add_marketplace_product_to_db,
                                         sender_error_to_tg)
from unit_economics.models import MarketplaceProduct

logger = logging.getLogger(__name__)


@sender_error_to_tg
def wb_categories_list(TOKEN_WB):
    """Возвращает список категорий товаров текущего пользователя"""
    main_data = wb_article_data_from_api(TOKEN_WB)
    categories_dict = {}
    for data in main_data:
        if data['subjectID'] not in categories_dict:
            categories_dict[data['subjectID']] = data['subjectName']
    return categories_dict


@sender_error_to_tg
def wb_comission_add_to_db():
    """
    Записывает комиссии ВБ в базу данных

    Входящие переменные:
        TOKEN_WB - токен учетной записи
    """
    accounts_wb = Account.objects.filter(
        platform=Platform.objects.get(
            platform_type=MarketplaceChoices.WILDBERRIES)
    )
    for account in accounts_wb:
        token_wb = account.authorization_fields['token']
        data_list = wb_comissions(token_wb)
        if data_list:
            goods_list = MarketplaceProduct.objects.filter(
                account=account, platform=Platform.objects.get(platform_type=MarketplaceChoices.WILDBERRIES))
            for data in data_list:
                for good_data in goods_list:
                    if good_data.category.category_number == data['subjectID']:
                        add_marketplace_comission_to_db(
                            good_data,
                            data['kgvpMarketplace'],
                            data['paidStorageKgvp'],
                            data['kgvpSupplier'],
                            data['kgvpSupplierExpress']
                        )


@sender_error_to_tg
def wb_logistic_add_to_db():
    """
    Записывает затраты на логистику ВБ в базу данных

    Входящие переменные:
        TOKEN_WB - токен учетной записи
    """
    accounts_wb = Account.objects.filter(
        platform=Platform.objects.get(
            platform_type=MarketplaceChoices.WILDBERRIES)
    )
    for account in accounts_wb:
        token_wb = account.authorization_fields['token']
        data_list = wb_logistic(token_wb)
        box_delivery_base = 0
        box_delivery_liter = 0
        comission = 0
        if data_list:
            for data in data_list:
                if data['warehouseName'] == 'Коледино':
                    box_delivery_base = data['boxDeliveryBase']
                    box_delivery_liter = data['boxDeliveryLiter']
                    break
        goods_data = MarketplaceProduct.objects.filter(
            account=account, platform=Platform.objects.get(platform_type=MarketplaceChoices.WILDBERRIES))
        for good in goods_data:
            height = good.height
            width = good.width
            length = good.length
            value = height * width * length / 1000
            box_delivery_base = float(
                str(box_delivery_base).replace(',', '.'))
            box_delivery_liter = float(
                str(box_delivery_liter).replace(',', '.'))
            if value <= 1:
                comission = box_delivery_base
            else:
                comission = box_delivery_base + \
                    box_delivery_liter * (value - 1)
            comission = round(comission, 2)
            add_marketplace_logistic_to_db(
                good, comission)


@sender_error_to_tg
def wb_article_price_info(TOKEN_WB):
    """
    Возвращает словарь типа {nm_id: price_with_discount}
    """
    main_data = wb_price_data_from_api(TOKEN_WB)

    article_price_info = {}
    if main_data:
        for data in main_data:

            discounted_price = data['sizes'][0]['discountedPrice']
            article_price_info[data['nmID']] = discounted_price
        return article_price_info


@sender_error_to_tg
def wb_products_data_to_db():
    """Записывает данные о продуктах ВБ в базу данных"""
    users = User.objects.all()
    for user in users:
        account_sklad, created = Account.objects.get_or_create(
            user=user,
            platform=Platform.objects.get(
                platform_type=MarketplaceChoices.MOY_SKLAD),
        )
        accounts_wb = Account.objects.filter(
            user=user,
            platform=Platform.objects.get(
                platform_type=MarketplaceChoices.WILDBERRIES)
        )
        for account in accounts_wb:
            token_wb = account.authorization_fields['token']
            main_data = wb_article_data_from_api(token_wb)
            for data in main_data:
                platform = Platform.objects.get(
                    platform_type=MarketplaceChoices.WILDBERRIES)
                name = data['title']
                sku = data['nmID']
                seller_article = data['vendorCode']
                barcode = data['sizes'][0]['skus'][0]
                category_number = data['subjectID']
                category_name = data['subjectName']
                width = data['dimensions']['width']
                height = data['dimensions']['height']
                length = data['dimensions']['length']
                weight = 0

                add_marketplace_product_to_db(
                    account_sklad, barcode,
                    account, platform, name,
                    sku, seller_article, category_number,
                    category_name, width,
                    height, length, weight)
