from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('slots/', include('bookings.urls')),
    path('', RedirectView.as_view(pattern_name='bookings:slot_list', permanent=False)),
]
