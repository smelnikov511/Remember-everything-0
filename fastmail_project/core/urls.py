from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmailViewSet

router = DefaultRouter()
router.register(r'emails', EmailViewSet, basename='email')

urlpatterns = [
    path('', include(router.urls)),
]

# fastmail/urls.py (главный)
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
    # path('api-auth/', include('rest_framework.urls')), # Для login/logout в браузере
]