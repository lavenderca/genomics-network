# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2016-11-22 15:40
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('network', '0018_auto_20161118_1204'),
    ]

    operations = [
        migrations.AddField(
            model_name='datarecommendation',
            name='hidden',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='userrecommendation',
            name='hidden',
            field=models.BooleanField(default=False),
        ),
    ]
