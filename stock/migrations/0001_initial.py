# Generated by Django 5.1 on 2024-09-10 17:06

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Status',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Имя статуса из маркетплейса')),
                ('color', models.CharField(max_length=7, verbose_name='Хекс код цвета вместе с #')),
                ('status_code', models.IntegerField(verbose_name='Целочисленный код статуса')),
                ('is_deletable', models.BooleanField(default=True, verbose_name='Можно удалить')),
                ('position', models.PositiveSmallIntegerField(verbose_name='Позиция в линейке статусов')),
                ('my_stock_status_name', models.CharField(max_length=255, verbose_name="Наименование статуса в 'Мой Склад'")),
            ],
            options={
                'verbose_name': 'Статус заказа на маркетплейсе',
                'verbose_name_plural': 'Статусы заказов на маркетплейсах',
            },
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.CharField(max_length=255, verbose_name='Номер заказа')),
                ('created_dt', models.DateField(verbose_name='Дата и время создания')),
                ('shipped_dt', models.DateField(null=True, verbose_name='Дата и время отгрузки')),
                ('total_price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Сумма всего заказа')),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='orders', to='core.account', verbose_name='Аккаунт, к которому относится заказ')),
                ('status', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='orders', to='stock.status', verbose_name='Статус заказа')),
            ],
            options={
                'verbose_name': 'Заказ',
                'verbose_name_plural': 'Заказы',
            },
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=1, verbose_name='Количество')),
                ('price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Цена позиции')),
                ('sticker', models.TextField(default='', verbose_name='Base64 представление стикера, получаемого по API')),
                ('is_express', models.BooleanField(default=False, verbose_name='Срочное?')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='stock.order')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='order_items', to='core.product')),
            ],
            options={
                'verbose_name': 'Позиция заказа',
                'verbose_name_plural': 'Позиции заказов',
            },
        ),
    ]
