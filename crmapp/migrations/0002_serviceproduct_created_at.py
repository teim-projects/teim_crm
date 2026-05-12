"""
Manual migration to add `created_at` to crmapp_serviceproduct.
This field was added by origin/bharat-new directly to models.py
without a corresponding migration file.
"""
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crmapp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='serviceproduct',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
