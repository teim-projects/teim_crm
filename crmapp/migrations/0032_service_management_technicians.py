# Generated by Django 5.2 on 2025-06-04 09:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crmapp', '0031_remove_techworklist_work_techworklist_work'),
    ]

    operations = [
        migrations.AddField(
            model_name='service_management',
            name='technicians',
            field=models.ManyToManyField(blank=True, to='crmapp.technicianprofile'),
        ),
    ]
