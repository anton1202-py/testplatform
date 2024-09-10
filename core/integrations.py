from typing import List

import requests
from django.db.models import Q
from requests import Session

from analyticalplatform.integrations import BaseIntegration
from core.enums import FieldsTypes


class BaseProductsIntegration(BaseIntegration):

    def get_object_available_fields(self) -> dict:
        from core.models import Product

        return {Product: ["sku", "barcode", "vendor", "name", "brand"]}

    def get_db_products(self):
        return self.account.products.all()

    def get_products(self) -> List[dict]:
        raise NotImplementedError

    def refresh_products(self):
        from core.models import Product

        platform_products_data = self.get_products() or []

        platform_products_barcodes_list = [item["barcode"] for item in platform_products_data]

        self.get_db_products().exclude(
            Q(barcode__in=platform_products_barcodes_list) | Q(has_manual_connection=True)
        ).delete()

        account_products = self.get_db_products()

        bulk_update_objects = []
        bulk_create_objects = []

        for product_data in platform_products_data:
            product_obj = next((item for item in account_products if item.barcode == product_data["barcode"]), None)
            if product_obj:
                for key in product_data:
                    if hasattr(product_obj, key):
                        setattr(product_obj, key, product_data[key])
                bulk_update_objects.append(product_obj)
            else:
                bulk_create_objects.append(Product(account=self.account, **product_data))

        self.update_existing_objects(Product, bulk_update_objects)
        self.create_new_objects(Product, bulk_create_objects)


class WildBerriesIntegration(BaseProductsIntegration):
    def get_products(self) -> List[dict] or None:
        resp = requests.post(
            "https://suppliers-api.wildberries.ru/content/v2/get/cards/list",
            json={"settings": {"cursor": {"limit": 1000}, "filter": {"withPhoto": -1}}},
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.get_auth_token()}"},
        )

        if resp.status_code != 200:
            return None

        resp = resp.json()
        cards = resp.get("cards")

        if not cards:
            return None

        result_data = []

        for card_data in cards:
            for size_data in card_data["sizes"]:
                result_item = {
                    "sku": card_data["nmID"],
                    "barcode": size_data["skus"][0],
                    "vendor": card_data["vendorCode"],
                    "name": card_data["title"],
                    "brand": card_data["brand"],
                }
                result_data.append(result_item)

        return result_data


class OZONIntegration(BaseProductsIntegration):
    auth_fields_description = {
        "token": {"name": "Токен", "type": FieldsTypes.TEXT, "max_length": 255},
        "client_id": {"name": "Идентификатор клиента", "type": FieldsTypes.TEXT, "max_length": 255},
    }

    def get_auth_token(self):
        return (
            self.account.authorization_fields.get("token", ""),
            self.account.authorization_fields.get("client_id", ""),
        )

    def get_products(self) -> List[dict] or None:
        token, client_id = self.get_auth_token()
        session = Session()

        session.headers.update(
            {"Client-Id": client_id, "Api-Key": token},
        )

        response = session.post(
            "https://api-seller.ozon.ru/v2/product/list",
            json={"filter": {"visibility": "ALL"}, "limit": 1000},
        )

        if response.status_code != 200:
            return

        products_data = response.json()["result"]["items"]
        products_ids = [product["product_id"] for product in products_data]

        response = session.post("https://api-seller.ozon.ru/v2/product/info/list", json={"product_id": products_ids})

        session.close()

        if response.status_code != 200:
            return

        products_full_info = response.json()["result"]["items"]
        result_data = []

        for description in products_full_info:
            result_data.append(
                {
                    "sku": description["sku"],
                    "barcode": description["barcodes"][0] if description["barcodes"] else "",
                    "vendor": description["offer_id"],
                    "name": description["name"],
                }
            )

        return result_data


class YandexIntegration(BaseProductsIntegration):
    def get_products(self) -> List[dict] | None:
        products = []

        session = Session()
        session.headers.update({"Authorization": f"Bearer {self.get_auth_token()}"})

        stores_ids = []

        business_id_resp = session.get(
            "https://api.partner.market.yandex.ru/campaigns/?page_size=1000",
        )

        if business_id_resp.status_code != 200:
            return

        campaigns_info = business_id_resp.json()
        pages_count = campaigns_info["pager"]["pagesCount"]
        current_page = campaigns_info["pager"]["currentPage"]

        stores_info = business_id_resp.json()["campaigns"]
        stores_ids.extend(store["business"]["id"] for store in stores_info)

        while current_page < pages_count:
            business_id_resp = session.get(
                f"https://api.partner.market.yandex.ru/campaigns/?page_size=1000&page={current_page + 1}",
            )

            if business_id_resp.status_code != 200:
                continue

            campaigns_info = business_id_resp.json()
            current_page = campaigns_info["pager"]["currentPage"]
            stores_info = campaigns_info["campaigns"]
            stores_ids.extend(store["business"]["id"] for store in stores_info)

        for store_id in stores_ids:
            products_response = session.post(
                f"https://api.partner.market.yandex.ru/businesses/{store_id}/offer-mappings/?limit=200",
                json={"offerIds": []},
            )

            if products_response.status_code != 200:
                break

            products_info = products_response.json()
            next_page_token = products_info["result"]["paging"]["nextPageToken"]
            products_data = products_info["result"]["offerMappings"]

            for product in products_data:
                item = {
                    "sku": product["offer"]["offerId"],
                    "barcode": product["offer"]["barcodes"][0] if product["offer"]["barcodes"] else "",
                    "vendor": product["offer"].get("vendorCode", ""),
                    "name": product["offer"]["name"],
                }
                products.append(item)

            while next_page_token:
                products_response = session.post(
                    f"https://api.partner.market.yandex.ru/businesses/{store_id}/offer-mappings/?limit=200&page_token={next_page_token}",
                    json={"offerIds": []},
                )

                if products_response.status_code != 200:
                    break

                products_info = products_response.json()
                next_page_token = products_info["result"]["paging"].get("nextPageToken", "")
                products_data = products_info["result"]["offerMappings"]

                for product in products_data:
                    item = {
                        "sku": product["offer"]["offerId"],
                        "barcode": product["offer"]["barcodes"][0] if product["offer"]["barcodes"] else "",
                        "vendor": product["offer"].get("vendorCode", ""),
                        "name": product["offer"]["name"],
                    }
                    products.append(item)

        session.close()

        return products


class SberMarketIntegration(BaseProductsIntegration):
    def get_products(self) -> List[dict] or None:
        return None


class MyWarehouseIntegration(BaseProductsIntegration):
    auth_fields_description = {
        "login": {"name": "Логин", "type": FieldsTypes.TEXT, "max_length": 255},
        "password": {"name": "Пароль", "type": FieldsTypes.PASSWORD, "max_length": 255},
    }

    def get_auth_token(self):
        return (
            self.account.authorization_fields.get("login", ""),
            self.account.authorization_fields.get("password", ""),
        )

    def get_products(self) -> List[dict] or None:
        session = requests.Session()
        session.auth = self.get_auth_token()
        resp = session.get("https://api.moysklad.ru/api/remap/1.2/entity/product")
        if resp.status_code != 200:
            return None

        rows = resp.json().get("rows")
        if not rows:
            return None

        all_items = []

        for row in rows:
            if row.get("barcodes"):
                for barcode_data in row.get("barcodes"):
                    for key in barcode_data:
                        all_items.append(
                            {"barcode": barcode_data[key], "sku": row["id"], "vendor": row["code"], "name": row["name"]}
                        )

        return all_items
