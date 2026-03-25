"""
Модуль сервисного слоя (business logic) приложения FastMail.

Назначение:
- Инкапсулирует бизнес-логику работы с письмами
- Отделяет логику от представлений (views) и моделей (models)
- Предоставляет статические методы для CRUD операций

Используемые паттерны:
- Service Layer Pattern
- Transaction Script (для атомарных операций)
"""

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth.models import User
from .models import Email, Folder, Profile
from typing import List, Optional
from rest_framework.exceptions import NotFound, PermissionDenied


# =============================================================================
# EMAIL SERVICE
# =============================================================================

class EmailService:
    """
    Сервис для управления email-письмами.
    
    Предоставляет методы для:
    - Отправки писем (send_email)
    - Получения списка писем (get_emails)
    - Просмотра письма (get_email_detail)
    - Перемещения между папками (move_email)
    - Удаления писем (delete_email)
    
    Все методы статические и не требуют создания экземпляра класса.
    """

    @staticmethod
    def get_system_folder(name: str) -> Folder:
        """
        Получение системной папки по имени.
        
        Args:
            name (str): Название системной папки 
                       (Inbox, Sent, Archive, Trash, Drafts)
        
        Returns:
            Folder: Объект папки
        
        Примечание:
            Использует get_or_create для автоматического создания папки,
            если она не существует. Это обеспечивает надёжность при 
            первом запуске приложения.
        """
        folder, _ = Folder.objects.get_or_create(name=name, owner=None)
        return folder

    @staticmethod
    def send_email(user: User, recipient: str, subject: str, body: str) -> Email:
        """
        Отправка нового письма.
        
        Логика работы:
        1. Создаёт письмо в папке 'Sent' для отправителя
        2. Если получатель зарегистрирован в системе:
           - Создаёт копию письма в его папке 'Inbox'
           - Копия помечается как непрочитанная (is_read=False)
        3. Если получатель не зарегистрирован:
           - Письмо сохраняется только у отправителя
        
        Args:
            user (User): Пользователь-отправитель
            recipient (str): Email получателя
            subject (str): Тема письма
            body (str): Текст письма
        
        Returns:
            Email: Созданное письмо отправителя
        
        Transaction:
            Операция атомарная (transaction.atomic).
            Если создание копии для получателя не удастся,
            письмо отправителя будет откачено.
        
        Пример:
            email = EmailService.send_email(
                user=request.user,
                recipient='friend@example.com',
                subject='Привет!',
                body='Как дела?'
            )
        """
        sent_folder = EmailService.get_system_folder('Sent')
        inbox_folder = EmailService.get_system_folder('Inbox')

        with transaction.atomic():
            # Создаём письмо для отправителя (в папку Sent)
            sent_email = Email.objects.create(
                owner=user,
                folder=sent_folder,
                sender=user.email,
                recipient=recipient,
                subject=subject,
                body=body,
                is_read=True  # Свои отправленные письма считаем прочитанными
            )

            # Проверяем, существует ли получатель в системе
            try:
                recipient_profile = Profile.objects.get(email_address=recipient)
                recipient_user = recipient_profile.user

                # Создаём копию для получателя в его Inbox
                Email.objects.create(
                    owner=recipient_user,
                    folder=inbox_folder,
                    sender=user.email,
                    recipient=recipient,
                    subject=subject,
                    body=body,
                    is_read=False  # Для получателя письмо не прочитано
                )
            except Profile.DoesNotExist:
                # Получатель не зарегистрирован - письмо только у отправителя
                # В реальном приложении здесь была бы отправка на внешний SMTP
                pass

        return sent_email

    @staticmethod
    def get_emails(user: User, folder_name: Optional[str] = None) -> List[Email]:
        """
        Получение списка писем пользователя.
        
        Args:
            user (User): Пользователь-владелец писем
            folder_name (str, optional): Название папки для фильтрации
        
        Returns:
            List[Email]: QuerySet с письмами
        
        Логика фильтрации:
            1. Базовый фильтр: owner=user, is_deleted=False
            2. Если указана папка:
               - Сначала ищем среди системных папок (owner=None)
               - Если не найдено, ищем среди пользовательских (owner=user)
        
        Пример:
            # Все письма пользователя
            emails = EmailService.get_emails(user)
            
            # Только письма из Inbox
            inbox_emails = EmailService.get_emails(user, folder_name='Inbox')
        """
        # Базовый запрос: письма пользователя, исключая удалённые
        queryset = Email.objects.filter(owner=user, is_deleted=False)

        if folder_name:
            try:
                # Пытаемся найти системную папку (owner=None)
                folder = Folder.objects.get(name=folder_name, owner=None)
                queryset = queryset.filter(folder=folder)
            except Folder.DoesNotExist:
                # Если системной нет, ищем пользовательскую папку
                try:
                    folder = Folder.objects.get(name=folder_name, owner=user)
                    queryset = queryset.filter(folder=folder)
                except Folder.DoesNotExist:
                    # Папка не найдена - возвращаем пустой queryset
                    queryset = Email.objects.none()

        return queryset

    @staticmethod
    def get_email_detail(user: User, email_id: int) -> Email:
        """
        Просмотр конкретного письма с отметкой о прочтении.
        
        Args:
            user (User): Пользователь-владелец
            email_id (int): ID письма для просмотра
        
        Returns:
            Email: Объект письма
        
        Side Effects:
            Если письмо не прочитано (is_read=False),
            оно автоматически помечается как прочитанное.
        
        Exceptions:
            NotFound: Если письмо не найдено или принадлежит другому пользователю
        
        Пример:
            email = EmailService.get_email_detail(request.user, email_id=5)
            print(email.subject, email.is_read)  # is_read теперь True
        """
        try:
            # Ищем письмо: должно принадлежать пользователю и не быть удалённым
            email = Email.objects.get(
                id=email_id, 
                owner=user, 
                is_deleted=False
            )
        except Email.DoesNotExist:
            raise NotFound("Письмо не найдено")

        # Автоматическая отметка о прочтении
        if not email.is_read:
            email.is_read = True
            email.save(update_fields=['is_read', 'updated_at'])

        return email

    @staticmethod
    def move_email(user: User, email_id: int, target_folder_name: str) -> Email:
        """
        Перемещение письма в другую папку.
        
        Args:
            user (User): Пользователь-владелец
            email_id (int): ID письма для перемещения
            target_folder_name (str): Название целевой папки
        
        Returns:
            Email: Обновлённое письмо
        
        Логика поиска папки:
            1. Ищем папку с указанным именем
            2. Папка может быть системной (owner=None) или принадлежать пользователю
            3. Если папка не найдена - создаём новую пользовательскую папку
        
        Exceptions:
            NotFound: Если письмо не найдено
        
        Пример:
            # Переместить письмо в архив
            email = EmailService.move_email(user, email_id=5, target_folder_name='Archive')
            
            # Переместить в корзину
            EmailService.move_email(user, email_id=5, target_folder_name='Trash')
        """
        try:
            email = Email.objects.get(
                id=email_id, 
                owner=user, 
                is_deleted=False
            )
        except Email.DoesNotExist:
            raise NotFound("Письмо не найдено")

        # Поиск папки: системная (owner=None) ИЛИ пользовательская (owner=user)
        folder = Folder.objects.filter(
            Q(name=target_folder_name) & (Q(owner=None) | Q(owner=user))
        ).first()

        if not folder:
            # Папка не найдена - создаём новую пользовательскую папку
            # Это позволяет пользователям создавать свои категории
            folder = Folder.objects.create(name=target_folder_name, owner=user)

        email.folder = folder
        email.save(update_fields=['folder', 'updated_at'])
        return email

    @staticmethod
    def delete_email(user: User, email_id: int) -> None:
        """
        Удаление письма (Soft Delete).
        
        Args:
            user (User): Пользователь-владелец
            email_id (int): ID письма для удаления
        
        Returns:
            None
        
        Логика:
            Письмо не удаляется физически из базы данных.
            Вместо этого устанавливается флаг is_deleted=True.
            
            Преимущества soft delete:
            - Возможность восстановления из корзины
            - Сохранение истории переписки
            - Аудит действий пользователя
        
        Exceptions:
            NotFound: Если письмо не найдено или уже удалено
        
        Пример:
            EmailService.delete_email(user, email_id=5)
            # Письмо теперь скрыто из всех выборок, кроме Trash
        """
        try:
            email = Email.objects.get(
                id=email_id, 
                owner=user, 
                is_deleted=False  # Не даём удалить уже удалённое
            )
        except Email.DoesNotExist:
            raise NotFound("Письмо не найдено")

        # Soft delete: устанавливаем флаг вместо физического удаления
        email.is_deleted = True
        email.save(update_fields=['is_deleted', 'updated_at'])
