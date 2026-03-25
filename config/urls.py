from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', RedirectView.as_view(pattern_name='login', permanent=True)),
    path('', include('reports.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
