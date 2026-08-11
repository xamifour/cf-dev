# cf-dev/cf_src/cf/urls.py

"""URL configuration for the CF project."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Organisation portal (normal users) — public landing at /
    path("", include("cf_users.urls")),
    # Platform explore: events, sermons, outreaches (visibility-aware)
    path("explore/", include("cf_operations.urls")),
    # Social network (platform-wide, authenticated users)
    path("social/", include("cf_social.urls")),
    # Versioned DRF APIs (one package per domain app under appsinn/*/api/)
    path("api/v1/", include("cf_utils.api.urls")),  # health/
    path("api/v1/users/", include("cf_users.api.urls")),
    path("api/v1/people/", include("cf_people.api.urls")),
    path("api/v1/operations/", include("cf_operations.api.urls")),
    path("api/v1/finance/", include("cf_finance.api.urls")),
    path("api/v1/communications/", include("cf_communications.api.urls")),
    path("api/v1/social/", include("cf_social.api.urls")),
    # Staff operations console
    path("admin/", admin.site.urls),
    # Optional allauth account flows (password reset, etc.)
    path("accounts/", include("allauth.urls")),
    # CKEditor 5 image upload endpoint (required by CKEditor5Widget reverse)
    path("ckeditor5/", include("django_ckeditor_5.urls")),
]

# Serve uploaded media in all environments when using local filesystem storage.
# In production behind a reverse proxy, prefer dedicated media hosting instead.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    try:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
            *urlpatterns,
        ]
    except ImportError:
        pass

admin.site.site_header = "CF Church Administration"
admin.site.site_title = "CF Admin"
admin.site.index_title = "Command centre"
