from django.urls import include, path
from rest_framework.routers import DefaultRouter
from unit_economics.views import ProductPriceMSViewSet, ProductPriceWBViewSet, ProductPriceOZONViewSet, \
    ProductMoySkladViewSet, ProductWBViewSet, ProductOZONViewSet

router = DefaultRouter()
router.register(r'product-create-db-my-sklad', ProductPriceMSViewSet)
router.register(r'product-create-db-wb', ProductPriceWBViewSet, basename='unit_economics')
router.register(r'product-create-db-ozon', ProductPriceOZONViewSet, basename='ozon_unit_economics')
router.register(r'product-my-sklad', ProductMoySkladViewSet, basename='moysklad_unit_economics')
router.register(r'product-wb', ProductWBViewSet, basename='wb_product_unit_economics')
router.register(r'product-ozon', ProductOZONViewSet, basename='ozon_product_unit_economics')

urlpatterns = [
    path('', include(router.urls)),
]

