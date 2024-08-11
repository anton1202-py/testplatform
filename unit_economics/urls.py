from django.urls import include, path
from rest_framework.routers import DefaultRouter
from unit_economics.views import ProductPriceViewSet

router = DefaultRouter()
router.register(r'product-price', ProductPriceViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

