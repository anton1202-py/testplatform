import datetime
from itertools import groupby

from django.db import transaction
from requests import Session

from analyticalplatform.integrations import BaseIntegration
from core.enums import FieldsTypes
from stock.enums import BaseStatus
from stock.utils import convert_date_format


class BaseOrdersIntegration(BaseIntegration):
    def get_object_available_fields(self):
        from stock.models import Order, OrderItem

        return {
            Order: ["status", "total_price", "shipped_dt"],
            OrderItem: ["price", "quantity", "sticker"],
        }

    @transaction.atomic
    def refresh_orders(self):
        from core.models import Product
        from stock.models import Order, OrderItem, Status

        orders = self.get_orders()
        account_order_numbers = [order["number"] for order in orders]

        account_orders = self.get_account_orders()
        account_orders.exclude(number__in=account_order_numbers).delete()

        bulk_update_orders = []
        bulk_create_orders = []

        bulk_update_order_items = []
        bulk_create_order_items = []

        product_skus = []
        statuses = Status.objects.all()

        for order in orders:
            product_skus.extend(product["sku"] for product in order["products"])
            order_obj = next((item for item in account_orders if item.number == order["number"]), None)

            if order_obj:
                for key in order:
                    if key == "products":
                        continue

                    if key == "status":
                        status_obj = next(
                            (status for status in statuses if status.status_code == order["status"]), None
                        )
                        setattr(order_obj, key, status_obj)
                        continue

                    if hasattr(order_obj, key):
                        setattr(order_obj, key, order[key])

                bulk_update_orders.append(order_obj)

            else:
                status_obj = next((status for status in statuses if status.status_code == order["status"]), None)
                bulk_create_orders.append(
                    Order(
                        account=self.account,
                        total_price=order["total_price"],
                        status=status_obj,
                        number=order["number"],
                        shipped_dt=order["shipped_dt"],
                        created_dt=order["created_dt"],
                    )
                )

        self.create_new_objects(Order, bulk_create_orders)
        self.update_existing_objects(Order, bulk_update_orders)

        db_orders = Order.objects.filter(number__in=account_order_numbers).values_list("number", "id")
        db_products = Product.objects.filter(sku__in=product_skus, account=self.account)
        db_orders_items = OrderItem.objects.filter(order__in=[item[1] for item in db_orders])

        for order in orders:
            order_id = next(filter(lambda x: x[0] == order["number"], db_orders), None)[1]

            for order_item in order["products"]:
                db_order_item = next((item for item in db_orders_items if item.product.sku == order_item["sku"]), None)

                if db_order_item:
                    for key in order_item:
                        if key == "sku":
                            continue

                        if hasattr(db_order_item, key):
                            setattr(db_order_item, key, order_item[key])

                    bulk_update_order_items.append(db_order_item)

                else:
                    db_product = next(filter(lambda x: x.sku == order_item["sku"], db_products), None)

                    if not db_product:
                        continue

                    bulk_create_order_items.append(
                        OrderItem(
                            order_id=order_id,
                            product=db_product,
                            quantity=order_item["quantity"],
                            price=order_item["price"],
                            sticker=order_item.get("sticker", ""),
                        )
                    )

        self.create_new_objects(OrderItem, bulk_create_order_items)
        self.update_existing_objects(OrderItem, bulk_update_order_items)

    def get_account_orders(self):
        return self.account.orders.all()

    def get_orders(self) -> list[dict]:
        raise NotImplementedError


class WildBerriesOrdersIntegration(BaseOrdersIntegration):
    MATCH_STATUSES = {
        "sold": BaseStatus.SHIPPED,
        "waiting": BaseStatus.NEW,
        "sorted": BaseStatus.ACCEPTED,
        "ready_for_pickup": BaseStatus.ASSEMBLED_SHIPMENT,
        "canceled": BaseStatus.CANCELED,
        "canceled_by_client": BaseStatus.RETURNED,
        "declined_by_client": BaseStatus.RETURNED,
        "defect": BaseStatus.RETURNED,
    }

    def get_orders(self) -> list[dict]:
        orders_info = list()
        order_items_info = dict()
        session = Session()
        session.headers.update(
            {
                "Authorization": f"Bearer {self.get_auth_token()}",
                "Content-Type": "application/json",
            }
        )

        resp = session.get(
            "https://suppliers-api.wildberries.ru/api/v3/orders",
            params={"limit": 100, "next": 0},
        )

        if resp.status_code != 200:
            return []

        data = resp.json()

        pagination, orders_items = data.get("next"), data.get("orders", [])

        for order_item in orders_items:
            order_items_info[order_item["id"]] = {
                "created_dt": order_item["createdAt"],
                "price": order_item["price"] / 100,
                "skus": order_item["skus"][0],
                "order_id": order_item["orderUid"],
            }

        response = session.post(
            "https://suppliers-api.wildberries.ru/api/v3/orders/stickers",
            json={"orders": list(order_items_info.keys())},
            params={"type": "svg", "width": 58, "height": 40},
        )

        stickers = response.json()["stickers"]
        for idx, sticker in enumerate(stickers):
            order_items_info[sticker["orderId"]].update({"sticker": sticker["file"]})

        response = session.post(
            "https://suppliers-api.wildberries.ru/api/v3/orders/status", json={"orders": list(order_items_info.keys())}
        )

        if response.status_code != 200:
            return []

        orders = response.json().get("orders", [])

        for order in orders:
            order_items_info[order["id"]].update(
                {"status": WildBerriesOrdersIntegration.MATCH_STATUSES[order["wbStatus"]]}
            )

        for key, group in groupby(order_items_info.values(), key=lambda x: x["order_id"]):
            products = list(group)
            order_info = {
                "number": key,
                "status": products[0]["status"],
                "created_dt": products[0]["created_dt"].split("T")[0],
                "shipped_dt": None,
            }

            for product in products:
                current_price = order_info.get("total_price", 0)
                order_info["total_price"] = current_price + product["price"]

                current_products = order_info.get("products", [])

                current_products.append(
                    {
                        "price": product["price"],
                        "quantity": 1,
                        "sku": product["skus"],
                        "sticker": product.get("sticker", ""),
                    }
                )
                order_info["products"] = current_products

            orders_info.append(order_info)

        return orders_info


class OzonOrdersIntegration(BaseOrdersIntegration):
    MATCH_STATUSES = {
        "awaiting_registration": BaseStatus.NEW,
        "acceptance_in_progress": BaseStatus.NEW,
        "awaiting_approve": BaseStatus.NEW,
        "awaiting_packaging": BaseStatus.ACCEPTED,
        "awaiting_deliver": BaseStatus.ASSEMBLED_SHIPMENT,
        "arbitration": BaseStatus.ASSEMBLED_SHIPMENT,
        "client_arbitration": BaseStatus.ASSEMBLED_SHIPMENT,
        "delivering": BaseStatus.SHIPPED,
        "driver_pickup": BaseStatus.SHIPPED,
        "sent_by_seller": BaseStatus.SHIPPED,
        "cancelled": BaseStatus.CANCELED,
        "not_accepted": BaseStatus.RETURNED,
    }

    def get_auth_token(self):
        return (
            self.account.authorization_fields.get("token", ""),
            self.account.authorization_fields.get("client_id", ""),
        )

    def get_orders(self) -> list:
        session = Session()
        token, client_id = self.get_auth_token()
        session.headers.update(
            {"Client-Id": client_id, "Api-Key": token, "Content-Type": "application/json"},
        )
        orders_info = list()

        now = datetime.datetime.now()
        ten_minutes_after = datetime.datetime.now() + datetime.timedelta(minutes=10)

        response = session.post(
            "https://api-seller.ozon.ru/v3/posting/fbs/list",
            json={
                "limit": 1000,
                "filter": {
                    "since": now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
                    "to": ten_minutes_after.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
                },
            },
        )

        if response.status_code != 200:
            return []

        data = response.json()
        pagination, orders = data.get("has_next"), data.get("postings", [])

        for order in orders:
            products = []
            total_price = 0
            for product in orders["products"]:
                products.append(
                    {
                        "sku": product["sku"],
                        "price": product["price"],
                        "quantity": product["quantity"],
                    }
                )
                total_price += product["price"]

            orders_info.append(
                {
                    "number": order["order_number"],
                    "shipped_dt": order["shipment_date"],
                    "created_dt": order["in_process_at"],
                    "status": OzonOrdersIntegration.MATCH_STATUSES[order["status"]],
                    "order_items": products,
                    "total_price": total_price,
                }
            )

        return orders_info


class YandexOrdersIntegration(BaseOrdersIntegration):
    MATCH_STATUSES = {
        "CANCELLED": BaseStatus.CANCELED,
        "DELIVERED": BaseStatus.SHIPPED,
        "DELIVERY": BaseStatus.CONFIRMED_COMPLETE,
        "PICKUP": BaseStatus.ASSEMBLED_SHIPMENT,
        "PROCESSING": BaseStatus.ACCEPTED,
        "PENDING": BaseStatus.NEW,
        "UNPAID": BaseStatus.ACCEPTED,
        "PLACING": BaseStatus.NEW,
        "RESERVED": BaseStatus.ACCEPTED,
        "PARTIALLY_RETURNED": BaseStatus.RETURNED,
        "RETURNED": BaseStatus.RETURNED,
        "UNKNOWN": BaseStatus.RETURNED,
    }

    def get_orders(self) -> list[dict]:
        orders_info = []
        session = Session()

        session.headers.update(
            {"Authorization": "Bearer y0_AgAAAAAd6I9zAAuQmgAAAAEBUDqyAADq_1Ojv7pLOrDY1qTYhBQc5jKvDQ"}
        )

        business_id_resp = session.get(
            "https://api.partner.market.yandex.ru/campaigns/?page_size=1000",
        )

        if business_id_resp.status_code != 200:
            return []

        campaigns_info = business_id_resp.json()
        campaigns_ids = [camp["id"] for camp in campaigns_info["campaigns"]]

        for campaign_id in campaigns_ids:
            resp = session.get(f"https://api.partner.market.yandex.ru/campaigns/{campaign_id}/orders")

            if resp.status_code != 200:
                continue

            orders = resp.json()["orders"]

            for order in orders:
                products = []
                for product in order.get("items", []):
                    products.append(
                        {
                            "price": product["buyerPrice"],
                            "quantity": product["count"],
                            "sku": product["offerId"],
                        }
                    )

                shipped_dt = None
                if shipments := order.get("delivery", {}).get("shipments"):
                    shipped_dt = shipments[0].get("shipmentDate")

                orders_info.append(
                    {
                        "number": f"{order['id']}",
                        "total_price": order["buyerTotal"],
                        "products": products,
                        "status": YandexOrdersIntegration.MATCH_STATUSES[order["status"]],
                        "created_dt": convert_date_format(order["creationDate"]),
                        "shipped_dt": convert_date_format(shipped_dt) if shipped_dt else None,
                    }
                )

        return orders_info


class MyWarehouseOrdersIntegration(BaseOrdersIntegration):
    MATCH_STATUSES = {
        "Новый": BaseStatus.NEW,
        "Подтвержден": BaseStatus.ACCEPTED,
        "Собран": BaseStatus.ASSEMBLED_SHIPMENT,
        "Отгружен": BaseStatus.SHIPPED,
        "Доставлен": BaseStatus.SHIPPED,
        "Возврат": BaseStatus.RETURNED,
        "Отменен": BaseStatus.CANCELED,
        "Cобран/Ожидает отгрузки": BaseStatus.ASSEMBLED_SHIPMENT,
        "Спорный": BaseStatus.NEW,
        "Доставляется": BaseStatus.SHIPPED,
        "Отменен в пути": BaseStatus.CANCELED,
        "Возврат/Компенсирован": BaseStatus.RETURNED,
        "Возвращен": BaseStatus.RETURNED,
        "Подтвержден/Можно комплектовать": BaseStatus.ASSEMBLED_SHIPMENT,
        "Отменен селлером": BaseStatus.CANCELED,
        "Брак": BaseStatus.RETURNED,
        "Просрочено": BaseStatus.RETURNED,
        "Передан службе доставки": BaseStatus.SHIPPED,
        "Возвращен после отмены в процессе": BaseStatus.RETURNED,
        "Просрочена сборка": BaseStatus.RETURNED,
        "Просрочена отгрузка": BaseStatus.RETURNED,
    }

    auth_fields_description = {
        "login": {"name": "Логин", "type": FieldsTypes.TEXT, "max_length": 255},
        "password": {"name": "Пароль", "type": FieldsTypes.PASSWORD, "max_length": 255},
    }

    def get_auth_token(self):
        return (
            self.account.authorization_fields.get("login", ""),
            self.account.authorization_fields.get("password", ""),
        )

    def get_orders(self) -> list[dict]:
        session = Session()
        session.auth = self.get_auth_token()
        orders_info = []
        orders_items_info = []

        response = session.get("https://api.moysklad.ru/api/remap/1.2/entity/customerorder", params={"limit": 100})

        if response.status_code != 200:
            return []

        data = response.json()

        for order in data["rows"]:
            resp = session.get(order["state"]["meta"]["href"])

            if resp.status_code != 200:
                continue

            status = resp.json()["name"]

            resp = session.get(order["positions"]["meta"]["href"])

            if resp.status_code != 200:
                continue

            data = resp.json()

            for order_item in data["rows"]:
                resp = session.get(order_item["meta"]["href"])
                if resp.status_code != 200:
                    continue

                sku = resp.json()["id"]

                order_item_info = {"quantity": order_item["quantity"], "price": order_item["price"] / 100, "sku": sku}
                orders_items_info.append(order_item_info)

            order_info = {
                "status": MyWarehouseOrdersIntegration.MATCH_STATUSES[status],
                "number": order["id"],
                "created_dt": order["created"].split()[0],
                "shipped_dt": (
                    order.get("deliveryPlannedMoment", "").split()[0]
                    if order.get("deliveryPlannedMoment", "").split()
                    else None
                ),
                "total_price": order["sum"],
                "products": orders_items_info,
            }

            orders_info.append(order_info)

        return orders_info
