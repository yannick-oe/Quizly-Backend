"""Root URL configuration for the core project."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("auth_app.api.urls")),
    path("api/", include("quiz_app.api.urls")),
]
