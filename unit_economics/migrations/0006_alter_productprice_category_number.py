# Generated by Django 5.1 on 2024-08-27 16:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('unit_economics', '0005_productprice_category_name_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productprice',
            name='category_number',
            field=models.IntegerField(blank=True, null=True, verbose_name='Номер категории'),
        ),
    ]
