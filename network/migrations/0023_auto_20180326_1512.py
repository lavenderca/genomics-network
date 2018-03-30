# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2018-03-26 19:12
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('network', '0022_auto_20180322_1118'),
    ]

    operations = [
        migrations.CreateModel(
            name='FeatureAttributes',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('feature_attributes', django.contrib.postgres.fields.jsonb.JSONField()),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('experiment_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='network.ExperimentType')),
                ('locus_group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='network.LocusGroup')),
            ],
        ),
        migrations.CreateModel(
            name='FeatureValues',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('feature_values', django.contrib.postgres.fields.jsonb.JSONField()),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True, null=True)),
                ('dataset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='network.Dataset')),
                ('locus_group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='network.LocusGroup')),
            ],
            options={
                'verbose_name': 'FeatureValues',
                'verbose_name_plural': 'FeatureValues',
            },
        ),
        migrations.AlterUniqueTogether(
            name='featurevalues',
            unique_together=set([('locus_group', 'dataset')]),
        ),
    ]