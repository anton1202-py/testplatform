from django.urls import include, path
from rest_framework.routers import DefaultRouter
from unit_economics.views import ProductPriceMSViewSet, ProductPriceWBViewSet

router = DefaultRouter()
router.register(r'product-price', ProductPriceMSViewSet)
router.register(r'product-price-wb', ProductPriceWBViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

