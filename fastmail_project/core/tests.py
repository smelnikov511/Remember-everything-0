from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from .models import Email, Folder

class EmailAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='pass')
        self.client.force_authenticate(user=self.user)
        self.inbox = Folder.objects.create(name='Inbox', owner=None)
        self.trash = Folder.objects.create(name='Trash', owner=None)

    def test_send_email(self):
        """Тест создания письма"""
        data = {
            'recipient': 'friend@example.com',
            'subject': 'Hello',
            'body': 'Test body'
        }
        response = self.client.post('/api/emails/', data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Email.objects.count(), 1)
        self.assertEqual(Email.objects.first().subject, 'Hello')

    def test_mark_as_read_on_retrieve(self):
        """Тест отметки прочтения при просмотре"""
        email = Email.objects.create(
            owner=self.user, folder=self.inbox, 
            sender='me', recipient='other', 
            subject='Sub', body='Body', is_read=False
        )
        response = self.client.get(f'/api/emails/{email.id}/')
        self.assertEqual(response.status_code, 200)
        email.refresh_from_db()
        self.assertTrue(email.is_read)

    def test_move_email(self):
        """Тест перемещения в корзину"""
        email = Email.objects.create(
            owner=self.user, folder=self.inbox, 
            sender='me', recipient='other', 
            subject='Sub', body='Body'
        )
        response = self.client.patch(f'/api/emails/{email.id}/move/', 
                                     {'folder_name': 'Trash'}, format='json')
        self.assertEqual(response.status_code, 200)
        email.refresh_from_db()
        self.assertEqual(email.folder.name, 'Trash')

    def test_soft_delete(self):
        """Тест мягкого удаления"""
        email = Email.objects.create(
            owner=self.user, folder=self.inbox, 
            sender='me', recipient='other', 
            subject='Sub', body='Body', is_deleted=False
        )
        response = self.client.delete(f'/api/emails/{email.id}/')
        self.assertEqual(response.status_code, 204)
        email.refresh_from_db()
        self.assertTrue(email.is_deleted)
        
        # Письмо не должно попадать в список
        list_response = self.client.get('/api/emails/')
        self.assertEqual(len(list_response.data), 0)