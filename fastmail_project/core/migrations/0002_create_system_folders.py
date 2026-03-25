from django.db import migrations


def create_system_folders(apps, schema_editor):
    Folder = apps.get_model('core', 'Folder')
    system_folders = ['Inbox', 'Sent', 'Archive', 'Trash', 'Drafts']
    for folder_name in system_folders:
        Folder.objects.get_or_create(name=folder_name, owner=None)


def remove_system_folders(apps, schema_editor):
    Folder = apps.get_model('core', 'Folder')
    Folder.objects.filter(owner=None).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_system_folders, remove_system_folders),
    ]
