from django.urls import include, path
from rest_framework.routers import DefaultRouter

from unit_economics.views import (AccountViewSet, BrandViewSet,
                                  MarketplaceProductViewSet, PlatformViewSet,
                                  ProductMoySkladViewSet, ProductNameViewSet,
                                  ProductPriceMSViewSet, ProfitabilityAPIView, UpdatePriceView,
                                  CalculateMarketplacePriceView, MarketplaceActionListView)

router = DefaultRouter()
router.register(r'product-create-db-my-sklad',
                ProductPriceMSViewSet, basename='create_db')
router.register(r'platforms', PlatformViewSet, basename='platform')
router.register(r'marketplace-products', MarketplaceProductViewSet,
                basename='marketplace-product')  # работает тестим
router.register(r'accounts', AccountViewSet, basename='account')
router.register(r'brands', BrandViewSet, basename='brand')
router.register(r'product-names', ProductNameViewSet, basename='product-name')
# router.register(r'commissions', MarketplaceCommissionViewSet, basename='commission')  # Не понятно надо ли это

urlpatterns = [
    path('', include(router.urls)),
    path('api/profitability/<int:user_id>/',
         ProfitabilityAPIView.as_view(), name='profitability-api'),
    path('unit_economics/update-price/', UpdatePriceView.as_view(), name='update-price'),
    path('calculate-marketplace-price/', CalculateMarketplacePriceView.as_view(), name='calculate-marketplace-price'),
    path('marketplace-actions/', MarketplaceActionListView.as_view(), name='marketplace-actions-list'),
]