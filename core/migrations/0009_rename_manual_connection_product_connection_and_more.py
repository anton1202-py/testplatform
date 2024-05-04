# Generated by Django 4.2.10 on 2024-04-11 14:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_alter_platform_platform_type'),
    ]

    operations = [
        migrations.RenameField(
            model_name='product',
            old_name='manual_connection',
            new_name='connection',
        ),
        migrations.AddField(
            model_name='product',
            name='has_manual_connection',
            field=models.BooleanField(default=False, verbose_name='Связь создана в ручную'),
        ),
    ]
