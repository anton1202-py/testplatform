from django.conf.urls.static import static
from django.conf import settings

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("rest_framework.urls", namespace="rest_framework")),
    path("api/", include("core.urls")),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
