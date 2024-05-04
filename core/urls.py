from django.apps import apps
from django.urls import include, path
from rest_framework import routers
from rest_framework.authtoken.views import obtain_auth_token

from .views import (
    AccountsViewSet,
    ProductViewSet,
    GetMarketplaceTypesAPIView,
    CreateAccountAPIView,
    ProductManualConnectionCreationAPIView,
    GetPlatformAuthFieldsDescriptionAPIView,
    ExportReportAPIView,
)

router = routers.DefaultRouter()
router.register(r"accounts", AccountsViewSet, basename="accounts")
router.register(r"products", ProductViewSet, basename="products")

urlpatterns = [
    path("", include(router.urls)),
    path("token/", obtain_auth_token, name="login"),
    path("marketplace-types/", GetMarketplaceTypesAPIView.as_view(), name="marketplace_types"),
    path(
        "platform-auth-fields/<int:platform_type>/",
        GetPlatformAuthFieldsDescriptionAPIView.as_view(),
        name="get_platform_auth_fields_description",
    ),
    path("create-account/", CreateAccountAPIView.as_view(), name="create_marketplace_account"),
    path(
        "create-manual-connection/", ProductManualConnectionCreationAPIView.as_view(), name="create_manual_connection"
    ),
    path("export-report/", ExportReportAPIView.as_view(), name="export_report"),
]

if apps.is_installed("stock"):
    from stock.urls import urlpatterns as stock_urlpatterns
    urlpatterns += stock_urlpatterns
