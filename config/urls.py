from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("webui.urls")),
    path("api/v1/auth/", include("users.urls")),
    path("api/v1/accounts/", include("accounts.urls")),
    path("api/v1/transactions/", include("transactions.urls")),
    path("api/v1/transfers/", include("transactions.urls_transfers")),
    path("api/v1/manager/", include("dashboard.urls_manager")),
    path("api/v1/director/", include("dashboard.urls_director")),
    path("api/v1/qr/", include("qr_payments.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
