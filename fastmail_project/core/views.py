from rest_framework import viewsets, status, decorators
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import Email
from .serializers import EmailSerializer, SendEmailSerializer, MoveEmailSerializer
from .services import EmailService

class EmailViewSet(viewsets.ModelViewSet):
    """
    API для управления почтой.
    """
    serializer_class = EmailSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Возвращаем только письма текущего пользователя, которые не удалены.
        Поддержка фильтрации по папке через query param ?folder=Inbox
        """
        user = self.request.user
        folder_name = self.request.query_params.get('folder')
        return EmailService.get_emails(user, folder_name)

    def retrieve(self, request, *args, **kwargs):
        """
        Переопределяем retrieve для отметки 'прочитано'.
        """
        instance = EmailService.get_email_detail(request.user, kwargs['pk'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Отправка письма.
        """
        serializer = SendEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = EmailService.send_email(
            user=request.user,
            **serializer.validated_data
        )
        # Возвращаем созданное письмо
        return Response(EmailSerializer(email).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """
        Удаление письма (Soft Delete).
        """
        EmailService.delete_email(request.user, kwargs['pk'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @decorators.action(detail=True, methods=['patch'])
    def move(self, request, *args, **kwargs):
        """
        Эндпоинт для перемещения письма в другую папку.
        PATCH /api/emails/{id}/move/
        Body: {"folder_name": "Archive"}
        """
        serializer = MoveEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = EmailService.move_email(
            request.user, 
            kwargs['pk'], 
            serializer.validated_data['folder_name']
        )
        return Response(EmailSerializer(email).data)