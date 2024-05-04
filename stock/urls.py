from django.urls import path, include
from rest_framework import routers

from stock.views import OrderItemsViewSet, GetOrdersCounts

router = routers.DefaultRouter()
router.register(r"order-items", OrderItemsViewSet, basename="order_items")

urlpatterns = [
    path("", include(router.urls)),
    path("get-orders-counts/", GetOrdersCounts.as_view(), name="get_orders_counts"),
]
