# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2018-03-30 14:20
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('network', '0023_auto_20180326_1512'),
    ]

    operations = [
        migrations.AddField(
            model_name='experiment',
            name='public',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='myuser',
            name='public',
            field=models.BooleanField(default=True),
        ),
    ]