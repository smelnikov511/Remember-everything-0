"""
Модуль представлений (views) приложения FastMail.

Содержит два типа представлений:
1. API Views (DRF) - для работы с frontend через AJAX/Fetch
2. Web Views (Django templates) - для рендеринга HTML-страниц

API использует Session Authentication - аутентификация через cookies Django.
"""

from rest_framework import viewsets, status, decorators
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404, render
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required

from .models import Email, Folder, Profile
from .serializers import EmailSerializer, SendEmailSerializer, MoveEmailSerializer, RegisterSerializer
from .services import EmailService


# =============================================================================
# API VIEWS (Django REST Framework)
# =============================================================================

class EmailViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления email-письмами.
    
    Предоставляет CRUD операции для работы с письмами:
    - list: GET /api/emails/ - список писем
    - create: POST /api/emails/ - отправить письмо
    - retrieve: GET /api/emails/{id}/ - просмотр письма
    - destroy: DELETE /api/emails/{id}/ - удаление письма
    - move: PATCH /api/emails/{id}/move/ - перемещение в папку
    
    Все операции требуют аутентификации пользователя.
    """
    serializer_class = EmailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Возвращает отфильтрованный список писем текущего пользователя.
        
        Query Parameters:
            folder (str, optional): Название папки для фильтрации 
                                   (Inbox, Sent, Archive, Trash)
        
        Returns:
            QuerySet: Письма пользователя, исключая удалённые (is_deleted=False)
        """
        user = self.request.user
        folder_name = self.request.query_params.get('folder')
        return EmailService.get_emails(user, folder_name)

    def retrieve(self, request, *args, **kwargs):
        """
        Просмотр конкретного письма с автоматической отметкой о прочтении.
        
        При получении письма оно автоматически помечается как прочитанное
        (is_read=True) в сервисном слое EmailService.get_email_detail().
        """
        instance = EmailService.get_email_detail(request.user, kwargs['pk'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Отправка нового письма.
        
        Request Body:
            recipient (str): Email получателя
            subject (str): Тема письма (макс. 255 символов)
            body (str): Текст письма
        
        Returns:
            Response: Созданное письмо с статусом 201 CREATED
        """
        serializer = SendEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = EmailService.send_email(
            user=request.user,
            **serializer.validated_data
        )
        return Response(EmailSerializer(email).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """
        Удаление письма (Soft Delete).
        
        Письмо не удаляется из БД физически, а помечается флагом is_deleted=True.
        Такие письма скрываются из всех выборок, кроме папки Trash.
        """
        EmailService.delete_email(request.user, kwargs['pk'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @decorators.action(detail=True, methods=['patch'])
    def move(self, request, *args, **kwargs):
        """
        Перемещение письма в другую папку.
        
        URL: PATCH /api/emails/{id}/move/
        
        Request Body:
            folder_name (str): Название целевой папки 
                              (Inbox, Sent, Archive, Trash или пользовательская)
        
        Returns:
            Response: Обновлённое письмо
        """
        serializer = MoveEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = EmailService.move_email(
            request.user,
            kwargs['pk'],
            serializer.validated_data['folder_name']
        )
        return Response(EmailSerializer(email).data)


# =============================================================================
# API АУТЕНТИФИКАЦИИ
# =============================================================================

@decorators.api_view(['POST'])
@decorators.permission_classes([AllowAny])
def api_login(request):
    """
    Вход пользователя в систему.
    
    URL: POST /api/login/
    
    Request Body:
        username (str): Имя пользователя
        password (str): Пароль
    
    Returns:
        Response: 
            200 OK: {"status": "ok", "user": {...}}
            401 Unauthorized: {"error": "Неверное имя пользователя или пароль"}
    
    Примечание:
        При успешном входе создаётся Django session cookie,
        которая используется для последующих запросов.
    """
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(request, username=username, password=password)

    if user is not None:
        login(request, user)
        return Response({
            'status': 'ok',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        })

    return Response(
        {'error': 'Неверное имя пользователя или пароль'},
        status=status.HTTP_401_UNAUTHORIZED
    )


@decorators.api_view(['POST'])
@decorators.permission_classes([IsAuthenticated])
def api_logout(request):
    """
    Выход пользователя из системы.
    
    URL: POST /api/logout/
    
    Returns:
        Response: {"status": "ok"}
    
    Примечание:
        Требует аутентификации. session cookie удаляется.
    """
    logout(request)
    return Response({'status': 'ok'})


@decorators.api_view(['POST'])
@decorators.permission_classes([AllowAny])
def api_register(request):
    """
    Регистрация нового пользователя.
    
    URL: POST /api/register/
    
    Request Body:
        username (str): Имя пользователя (уникальное)
        email (str): Email (уникальный)
        password (str): Пароль (мин. 8 символов)
    
    Returns:
        Response:
            201 Created: {"status": "ok", "user": {...}}
            400 Bad Request: {"error": "..."}
    
    Примечание:
        После регистрации пользователь автоматически входит в систему.
        Создаётся профиль (Profile) с email_address через сигнал post_save.
    """
    from django.contrib.auth.models import User

    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')

    if not username or not email or not password:
        return Response(
            {'error': 'Все поля обязательны'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if User.objects.filter(username=username).exists():
        return Response(
            {'error': 'Пользователь с таким именем уже существует'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if User.objects.filter(email=email).exists():
        return Response(
            {'error': 'Email уже зарегистрирован'},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = User.objects.create_user(username=username, email=email, password=password)
    login(request, user)

    return Response({
        'status': 'ok',
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email
        }
    }, status=status.HTTP_201_CREATED)


@decorators.api_view(['GET'])
@decorators.permission_classes([IsAuthenticated])
def api_me(request):
    """
    Получение информации о текущем авторизованном пользователе.
    
    URL: GET /api/me/
    
    Returns:
        Response: {"id": int, "username": str, "email": str}
    
    Примечание:
        Требует аутентификации. Используется frontend для проверки сессии.
    """
    return Response({
        'id': request.user.id,
        'username': request.user.username,
        'email': request.user.email
    })


# =============================================================================
# WEB VIEWS (Django Templates)
# =============================================================================
# Эти функции рендерят HTML-страницы для frontend.
# Доступ требует аутентификации (декоратор @login_required).

@login_required
def web_inbox(request):
    """
    Страница входящих писем.
    
    URL: /inbox/
    Template: core/inbox.html
    
    Примечание:
        @login_required перенаправляет на LOGIN_URL (/login/) 
        если пользователь не авторизован.
    """
    return render(request, 'core/inbox.html')


@login_required
def web_sent(request):
    """
    Страница отправленных писем.
    
    URL: /sent/
    Template: core/sent.html
    """
    return render(request, 'core/sent.html')


@login_required
def web_archive(request):
    """
    Страница архива.
    
    URL: /archive/
    Template: core/archive.html
    """
    return render(request, 'core/archive.html')


@login_required
def web_trash(request):
    """
    Страница корзины (удалённые письма).
    
    URL: /trash/
    Template: core/trash.html
    """
    return render(request, 'core/trash.html')


@login_required
def web_compose(request):
    """
    Страница написания нового письма.
    
    URL: /compose/
    Template: core/compose.html
    """
    return render(request, 'core/compose.html')


@login_required
def web_email_detail(request, email_id):
    """
    Страница просмотра конкретного письма.
    
    URL: /email/<int:email_id>/
    Template: core/email_detail.html
    
    Args:
        request: HTTP запрос
        email_id (int): ID письма для просмотра
    """
    return render(request, 'core/email_detail.html', {'email_id': email_id})


def web_login(request):
    """
    Страница входа пользователя.
    
    URL: /login/
    Template: core/login.html
    
    Примечание:
        Если пользователь уже авторизован, 
        перенаправляется на /inbox/
    """
    if request.user.is_authenticated:
        return render(request, 'core/inbox.html')
    return render(request, 'core/login.html')


def web_register(request):
    """
    Страница регистрации нового пользователя.
    
    URL: /register/
    Template: core/register.html
    
    Примечание:
        Если пользователь уже авторизован,
        перенаправляется на /inbox/
    """
    if request.user.is_authenticated:
        return render(request, 'core/inbox.html')
    return render(request, 'core/register.html')