# Generated by Django 5.0 on 2025-05-26 10:23

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('crmapp', '0011_remove_quotation_management_technician_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='quotation_management',
            old_name='gst_checkbox',
            new_name='apply_gst',
        ),
    ]
