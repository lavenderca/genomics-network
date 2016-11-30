# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2016-11-23 14:43
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('network', '0019_auto_20161122_1040'),
    ]

    operations = [
        migrations.CreateModel(
            name='DataFavorite',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('favorite', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='network.Dataset')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='network.MyUser')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='UserFavorite',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('favorite', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorite', to='network.MyUser')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='network.MyUser')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
