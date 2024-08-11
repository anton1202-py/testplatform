from django.conf.urls.static import static
from django.conf import settings

from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path("admin/", admin.site.urls),
    path("api/", include("rest_framework.urls", namespace="rest_framework")),
    path("api/", include("core.urls")),
    path("api/unit_economics/", include("unit_economics.urls")),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
