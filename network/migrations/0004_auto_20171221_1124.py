# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2017-12-21 16:24
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('network', '0003_auto_20171218_1215'),
    ]

    operations = [
        migrations.CreateModel(
            name='DatasetIntersectionJson',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('intersection_values', django.contrib.postgres.fields.jsonb.JSONField()),
                ('dataset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='network.Dataset')),
                ('locus_group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='network.LocusGroup')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='datasetintersectionjson',
            unique_together=set([('locus_group', 'dataset')]),
        ),
    ]
