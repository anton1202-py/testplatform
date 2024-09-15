from django.urls import include, path
from rest_framework.routers import DefaultRouter

from unit_economics.views import (  # ProductsByCategoryAPIView)
    AccountViewSet, BrandViewSet, CalculateMarketplacePriceView,
    MarketplaceActionListView, MarketplaceProductPriceWithProfitabilityViewSet,
    MarketplaceProductViewSet, PlatformViewSet, ProductMoySkladViewSet,
    ProductNameViewSet, ProductPriceMSViewSet, ProfitabilityAPIView,
    TopSelectorsViewSet, UpdatePriceView, UserIdView, CalculateMPPriceView)

router = DefaultRouter()
router.register(r'product-create-db-my-sklad',
                ProductPriceMSViewSet, basename='create_db')
router.register(r'platforms', PlatformViewSet, basename='platform')
router.register(r'marketplace-products', MarketplaceProductViewSet,
                basename='marketplace-product')  # работает тестим
router.register(r'accounts', AccountViewSet, basename='account')
# router.register(r'topselectors', TopSelectorsViewSet, basename='topselectors')
router.register(r'brands', BrandViewSet, basename='brand')
router.register(r'product-names', ProductNameViewSet, basename='product-name')
router.register(r'profitability-fifo', MarketplaceProductPriceWithProfitabilityViewSet,
                basename='profitability-and-fifo')

urlpatterns = [
    path('', include(router.urls)),
    path('profitabilitys/<int:user_id>/',
         ProfitabilityAPIView.as_view(), name='profitability-api'),
    # path('profitability/<int:user_id>/products_by_category/', ProductsByCategoryAPIView.as_view(),
    #      name='products_by_category'),
    path('unit_economics/update-price/',
         UpdatePriceView.as_view(), name='update-price'),
    path('calculate-marketplace-price/', CalculateMarketplacePriceView.as_view(),
         name='calculate-marketplace-price'),
    path('marketplace-actions/', MarketplaceActionListView.as_view(),
         name='marketplace-actions-list'),
    path('user-id/', UserIdView.as_view(), name='user-id'),
    path('topselectors/', TopSelectorsViewSet.as_view(), name='topselectors'),
    path('calculate-price/', CalculateMPPriceView.as_view(), name='new_price'),
]
