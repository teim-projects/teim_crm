# Generated by Django 5.2 on 2025-06-04 06:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('crmapp', '0028_remove_techworklist_work_techworklist_work'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='technicianprofile',
            name='password',
        ),
    ]
