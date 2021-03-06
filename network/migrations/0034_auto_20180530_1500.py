# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2018-05-30 19:00
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('network', '0033_auto_20180522_1159'),
    ]

    operations = [
        migrations.AddField(
            model_name='experiment',
            name='color',
            field=models.CharField(blank=True, default=None, max_length=7, null=True),
        ),
        migrations.AddField(
            model_name='experiment',
            name='use_default_color',
            field=models.BooleanField(default=True),
        ),
    ]
