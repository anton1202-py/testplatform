import datetime
import logging

from django.db.models import F
from rest_framework import filters, mixins, status, views, viewsets
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend

from stock.models import OrderItem
from stock.serializers import OrderItemSerializer


class OrderItemsViewSet(
    viewsets.GenericViewSet,
    mixins.ListModelMixin,
):
    queryset = OrderItem.objects.all()

    serializer_class = OrderItemSerializer

    filter_backends = [filters.OrderingFilter, DjangoFilterBackend, filters.SearchFilter]

    filterset_fields = {
        "order__account": ["exact", "in"],
        "order__account__platform__platform_type": ["exact", "in", "icontains"],
        "product__brand": ["icontains"],
        "product__name": ["icontains"],
        "product__barcode": ["icontains"],
        "order__number": ["icontains"],
    }

    search_fields = [
        "product__name",
        "product__brand",
        "product__barcode",
        "order__account__platform__platform_type",
        "order__number",
    ]

    ordering_fields = [
        "product__brand",
        "order__created_dt",
        "order__shipped_dt",
        "order__status__status_code",
    ]

    def get_queryset(self):
        queryset = super().get_queryset()
        orders_type = self.request.GET.get("orders_type")

        today = datetime.datetime.today()
        start_date = datetime.datetime(year=today.year, month=today.month, day=today.day, hour=0, minute=0,
                                       second=0)
        end_date = datetime.datetime(year=today.year, month=today.month, day=today.day, hour=23, minute=59,
                                     second=59)

        if orders_type == "0":
            queryset = queryset.filter(is_express=True)
        elif orders_type == "1":
            queryset = queryset.filter(order__created_dt__gte=start_date, order__created_dt__lte=end_date)
        elif orders_type == "2":
            queryset = (queryset.exclude(order__created_dt__gte=start_date, order__created_dt__lte=end_date)
                        .exclude(is_express=True))
        return (
            queryset.filter(order__account__user=self.request.user)
            .annotate(
                order_number=F('order__number'),
                order_status_name=F('order__status__name'),
                order_status_color=F('order__status__color'),
                platform_name=F('order__account__platform__name'),
                product_name=F('product__name'),
                product_brand=F('product__brand'),
                product_barcode=F('product__barcode'),
                created_dt=F('order__created_dt'),
                shipped_dt=F('order__shipped_dt'),
            ).order_by('order_number'))


class GetOrdersCounts(views.APIView):
    def get(self, request, *args, **kwargs):
        queryset = OrderItem.objects.filter(order__account__user=request.user)

        today = datetime.datetime.today()
        start_date = datetime.datetime(year=today.year, month=today.month, day=today.day, hour=0, minute=0,
                                       second=0)
        end_date = datetime.datetime(year=today.year, month=today.month, day=today.day, hour=23, minute=59,
                                     second=59)

        all_count = queryset.count()
        express_count = queryset.filter(is_express=True).count()
        today_count = queryset.filter(order__created_dt__gte=start_date, order__created_dt__lte=end_date).count()
        other_count = (queryset.exclude(order__created_dt__gte=start_date, order__created_dt__lte=end_date)
                       .exclude(is_express=True).count())

        return Response(data={"all": all_count, "urgent": express_count, "today": today_count, "other": other_count})
