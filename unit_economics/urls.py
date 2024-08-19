from django.urls import include, path
from rest_framework.routers import DefaultRouter
from unit_economics.views import ProductPriceMSViewSet, ProductPriceWBViewSet, ProductPriceOZONViewSet, \
    ProductMoySkladViewSet, ProductWBViewSet, ProductOZONViewSet

router = DefaultRouter()
router.register(r'product-create-db-my-sklad', ProductPriceMSViewSet)
router.register(r'product-create-db-wb', ProductPriceWBViewSet)
router.register(r'product-create-db-ozon', ProductPriceOZONViewSet)
router.register(r'product-my-sklad', ProductMoySkladViewSet)
router.register(r'product-wb', ProductWBViewSet)
router.register(r'product-ozon', ProductOZONViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

