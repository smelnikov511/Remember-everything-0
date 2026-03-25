from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EmailViewSet,
    api_login, api_logout, api_register, api_me,
    web_inbox, web_sent, web_archive, web_trash, web_compose, web_email_detail,
    web_login, web_register
)

router = DefaultRouter()
router.register(r'emails', EmailViewSet, basename='email')

urlpatterns = [
    # API эндпоинты
    path('', include(router.urls)),
    path('login/', api_login, name='api-login'),
    path('logout/', api_logout, name='api-logout'),
    path('register/', api_register, name='api-register'),
    path('me/', api_me, name='api-me'),
]

# Web URLs (frontend страницы)
web_urlpatterns = [
    path('', web_inbox, name='web-inbox'),
    path('login/', web_login, name='web-login'),
    path('register/', web_register, name='web-register'),
    path('inbox/', web_inbox, name='web-inbox-list'),
    path('sent/', web_sent, name='web-sent'),
    path('archive/', web_archive, name='web-archive'),
    path('trash/', web_trash, name='web-trash'),
    path('compose/', web_compose, name='web-compose'),
    path('email/<int:email_id>/', web_email_detail, name='web-email-detail'),
]
