from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("", include("marketplace.urls")),
    path("", include("orders.urls")),
    path("", include("payments.urls")),
    path("", include("riders.urls")),
    path("", include("aftersales.urls")),
]

# While developing, let Django serve uploaded files (shop photos, documents).
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
