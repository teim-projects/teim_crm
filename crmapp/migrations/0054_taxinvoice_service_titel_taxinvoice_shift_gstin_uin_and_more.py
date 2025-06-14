# Generated by Django 5.2.3 on 2025-06-13 17:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crmapp', '0053_remove_taxinvoice_hsn_sac_taxinvoiceitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='taxinvoice',
            name='service_titel',
            field=models.CharField(default=1, max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='taxinvoice',
            name='shift_gstin_uin',
            field=models.CharField(default=1, max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='taxinvoice',
            name='shifttopartystate',
            field=models.CharField(default=1, max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='taxinvoice',
            name='shifttopartystatecode',
            field=models.CharField(default=1, max_length=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='taxinvoice',
            name='sold_gstin_uin',
            field=models.CharField(default=1, max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='taxinvoice',
            name='soldtopartystate',
            field=models.CharField(default=1, max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='taxinvoice',
            name='soldtopartystatecode',
            field=models.CharField(default=1, max_length=10),
            preserve_default=False,
        ),
    ]
