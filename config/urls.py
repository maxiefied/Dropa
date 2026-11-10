from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path, re_path
from django.views.static import serve as serve_static

from . import private_files


def health(request):
    """The host pings this to check the site is up."""
    return HttpResponse("ok")


urlpatterns = [
    path("healthz", health),
    path("admin/", admin.site.urls),
    path("private/<path:path>", private_files.serve, name="private_file"),
    path("", include("accounts.urls")),
    path("", include("marketplace.urls")),
    path("", include("orders.urls")),
    path("", include("payments.urls")),
    path("", include("riders.urls")),
    path("", include("aftersales.urls")),
    path("", include("payouts.urls")),
]

# Public uploads (menu photos, rider photos) are served by Django itself when
# they live on the server's own disk. With S3 storage they come from the bucket.
if not settings.USE_S3_MEDIA:
    urlpatterns += [
        re_path(
            rf"^{settings.MEDIA_URL.lstrip('/')}(?P<path>.*)$",
            serve_static,
            {"document_root": settings.MEDIA_ROOT},
        )
    ]
