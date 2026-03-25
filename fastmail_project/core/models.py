"""
Модуль моделей данных приложения FastMail.

Определяет структуру базы данных для хранения:
- Профилей пользователей (Profile)
- Папок для писем (Folder)
- Самих писем (Email)
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from typing import Optional


# =============================================================================
# МОДЕЛИ
# =============================================================================

class Profile(models.Model):
    """
    Профиль пользователя - расширение стандартной модели User.
    
    Назначение:
    - Связывает пользователя с его email-адресом в системе
    - Позволяет отправлять письма другим пользователям по email
    
    Поля:
        user: Связь один-к-одному со стандартной моделью User
        email_address: Уникальный email пользователя в системе
        created_at: Дата и время создания профиля
    
    Пример использования:
        # Найти пользователя по email
        profile = Profile.objects.get(email_address='user@example.com')
        user = profile.user
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='profile',
        help_text="Связь со стандартной моделью пользователя Django"
    )
    email_address = models.EmailField(
        unique=True,
        help_text="Уникальный email-адрес пользователя в системе"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Дата и время создания профиля"
    )

    class Meta:
        verbose_name = "Профиль"
        verbose_name_plural = "Профили"

    def __str__(self):
        return f"{self.user.username} ({self.email_address})"


class Folder(models.Model):
    """
    Папка для хранения писем.
    
    Назначение:
    - Организует письма по категориям (Входящие, Отправленные, Архив, Корзина)
    - Поддерживает системные папки (owner=None) и пользовательские
    
    Типы папок:
        1. Системные (owner=None): Inbox, Sent, Archive, Trash, Drafts
           - Доступны всем пользователям
           - Создаются автоматически при миграции
        2. Пользовательские (owner=User):
           - Персональные папки пользователя
           - Создаются динамически
    
    Поля:
        name: Название папки (уникальное)
        owner: Владелец папки (null для системных папок)
    
    Пример использования:
        # Получить системную папку
        inbox = Folder.objects.get(name='Inbox', owner=None)
        
        # Создать пользовательскую папку
        custom_folder = Folder.objects.create(name='Work', owner=user)
    """
    name = models.CharField(
        max_length=50, 
        unique=True,
        help_text="Название папки (Inbox, Sent, Archive, Trash или пользовательское)"
    )
    owner = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='folders',
        help_text="Владелец папки. NULL для системных папок"
    )

    class Meta:
        verbose_name = "Папка"
        verbose_name_plural = "Папки"
        # Индексы для ускорения поиска по name и owner
        indexes = [
            models.Index(fields=['name', 'owner']),
        ]

    def __str__(self):
        owner_info = f" (user: {self.owner.username})" if self.owner else " (system)"
        return f"{self.name}{owner_info}"


class Email(models.Model):
    """
    Модель электронного письма.
    
    Назначение:
    - Хранит всю информацию о письме (отправитель, получатель, тема, текст)
    - Отслеживает статус прочтения и принадлежность к папке
    - Поддерживает мягкое удаление (soft delete)
    
    Поля:
        owner: Владелец письма (пользователь, которому оно принадлежит)
        folder: Папка, в которой находится письмо
        sender: Email отправителя
        recipient: Email получателя
        subject: Тема письма (макс. 255 символов)
        body: Текст письма
        is_read: Флаг прочтения (True/False)
        is_deleted: Флаг удаления (soft delete)
        created_at: Дата и время создания
        updated_at: Дата и время последнего обновления
    
    Индексы:
        - (owner, is_deleted): Для быстрой выборки писем пользователя
        - (folder, is_deleted): Для быстрой выборки писем из папки
    
    Пример использования:
        # Получить все непрочитанные письма пользователя
        unread = Email.objects.filter(owner=user, is_read=False)
        
        # Пометить письмо как прочитанное
        email.is_read = True
        email.save(update_fields=['is_read', 'updated_at'])
    """
    owner = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='emails',
        help_text="Пользователь-владелец письма"
    )
    folder = models.ForeignKey(
        Folder, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='emails',
        help_text="Папка, в которой находится письмо"
    )

    sender = models.EmailField(
        help_text="Email-адрес отправителя"
    )
    recipient = models.EmailField(
        help_text="Email-адрес получателя"
    )
    subject = models.CharField(
        max_length=255,
        help_text="Тема письма (максимум 255 символов)"
    )
    body = models.TextField(
        help_text="Текст сообщения"
    )

    is_read = models.BooleanField(
        default=False,
        help_text="Флаг: прочитано ли письмо"
    )
    is_deleted = models.BooleanField(
        default=False,
        help_text="Флаг: удалено ли письмо (soft delete)"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Дата и время создания письма"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Дата и время последнего обновления"
    )

    class Meta:
        verbose_name = "Письмо"
        verbose_name_plural = "Письма"
        ordering = ['-created_at']  # Новые письма сверху
        indexes = [
            models.Index(fields=['owner', 'is_deleted'], name='owner_deleted_idx'),
            models.Index(fields=['folder', 'is_deleted'], name='folder_deleted_idx'),
        ]

    def __str__(self):
        return f"{self.subject} ({self.owner.username})"