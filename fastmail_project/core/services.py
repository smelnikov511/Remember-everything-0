from django.db import transaction
from django.utils import timezone
from .models import Email, Folder
from typing import List, Optional
from rest_framework.exceptions import NotFound, PermissionDenied

class EmailService:
    
    @staticmethod
    def get_system_folder(name: str) -> Folder:
        """Получение системной папки по имени."""
        folder, _ = Folder.objects.get_or_create(name=name, owner=None)
        return folder

    @staticmethod
    def send_email(user: User, recipient: str, subject: str, body: str) -> Email:
        """
        1. Отправка письма.
        Логика: Создаем письмо в папке 'Отправленные' для пользователя.
        В реальном мире здесь был бы вызов SMTP сервиса или Celery task.
        """
        sent_folder = EmailService.get_system_folder('Sent')
        
        with transaction.atomic():
            email = Email.objects.create(
                owner=user,
                folder=sent_folder,
                sender=user.email,
                recipient=recipient,
                subject=subject,
                body=body,
                is_read=True # Свои отправленные письма считаем прочитанными
            )
            # Примечание: В полноценной системе здесь мы бы создали копию письма 
            # для получателя в его папку 'Inbox'. Для упрощения задачи делаем только запись для отправителя.
        return email

    @staticmethod
    def get_emails(user: User, folder_name: Optional[str] = None) -> List[Email]:
        """
        2. Получение списка писем.
        Фильтрация по папке и исключение удаленных.
        """
        queryset = Email.objects.filter(owner=user, is_deleted=False)
        
        if folder_name:
            try:
                folder = Folder.objects.get(name=folder_name, owner=None) # Системные папки
                queryset = queryset.filter(folder=folder)
            except Folder.DoesNotExist:
                # Если папка пользовательская
                folder = Folder.objects.get(name=folder_name, owner=user)
                queryset = queryset.filter(folder=folder)
                
        return queryset

    @staticmethod
    def get_email_detail(user: User, email_id: int) -> Email:
        """
        3. Просмотр письма + отметка о прочтении.
        """
        try:
            email = Email.objects.get(id=email_id, owner=user, is_deleted=False)
        except Email.DoesNotExist:
            raise NotFound("Письмо не найдено")
        
        if not email.is_read:
            email.is_read = True
            email.save(update_fields=['is_read', 'updated_at'])
            
        return email

    @staticmethod
    def move_email(user: User, email_id: int, target_folder_name: str) -> Email:
        """
        4. Перемещение между папками.
        """
        try:
            email = Email.objects.get(id=email_id, owner=user, is_deleted=False)
        except Email.DoesNotExist:
            raise NotFound("Письмо не найдено")
            
        # Поиск папки (сначала системные, потом личные)
        folder = Folder.objects.filter(name=target_folder_name).filter(
            models.Q(owner=None) | models.Q(owner=user)
        ).first()
        
        if not folder:
            # Создаем если нет (опционально, зависит от требований)
            folder = Folder.objects.create(name=target_folder_name, owner=user)
            
        email.folder = folder
        email.save(update_fields=['folder', 'updated_at'])
        return email

    @staticmethod
    def delete_email(user: User, email_id: int) -> None:
        """
        5. Удаление письма (Soft Delete).
        """
        try:
            email = Email.objects.get(id=email_id, owner=user, is_deleted=False)
        except Email.DoesNotExist:
            raise NotFound("Письмо не найдено")
            
        email.is_deleted = True
        email.save(update_fields=['is_deleted', 'updated_at'])
