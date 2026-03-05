from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from typing import Optional

class Folder(models.Model):
    """
    Папки писем. Системные папки идентифицируются по name.
    """
    name = models.CharField(max_length=50, unique=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='folders')
    # null=True для owner позволяет создать глобальные системные папки (Inbox, Trash) для всех,
    # либо можно создавать персональные. Для упрощения сделаем системные без owner.
    
    class Meta:
        verbose_name = "Папка"
        verbose_name_plural = "Папки"

    def __str__(self):
        return self.name

class Email(models.Model):
    """
    Модель письма.
    """
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='emails')
    folder = models.ForeignKey(Folder, on_delete=models.SET_NULL, null=True, related_name='emails')
    
    sender = models.EmailField()
    recipient = models.EmailField()
    subject = models.CharField(max_length=255)
    body = models.TextField()
    
    is_read = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False) # Soft delete
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Письмо"
        verbose_name_plural = "Письма"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', 'is_deleted']), # Оптимизация выборки
            models.Index(fields=['folder', 'is_deleted']),
        ]

    def __str__(self):
        return f"{self.subject} ({self.owner.username})"