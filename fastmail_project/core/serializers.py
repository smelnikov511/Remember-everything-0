from rest_framework import serializers
from .models import Email, Folder

class EmailSerializer(serializers.ModelSerializer):
    folder_name = serializers.CharField(source='folder.name', read_only=True)
    
    class Meta:
        model = Email
        fields = [
            'id', 'sender', 'recipient', 'subject', 'body', 
            'is_read', 'folder_name', 'created_at', 'is_deleted'
        ]
        read_only_fields = ['id', 'sender', 'is_deleted', 'created_at', 'folder_name']

class SendEmailSerializer(serializers.Serializer):
    recipient = serializers.EmailField()
    subject = serializers.CharField(max_length=255)
    body = serializers.CharField()

class MoveEmailSerializer(serializers.Serializer):
    folder_name = serializers.CharField(max_length=50)