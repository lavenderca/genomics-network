# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2018-03-15 16:45
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('network', '0017_recommendation_similarity'),
    ]

    operations = [
        migrations.AlterField(
            model_name='similarity',
            name='experiment_1',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sim_experiment_1', to='network.Experiment'),
        ),
        migrations.AlterField(
            model_name='similarity',
            name='experiment_2',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sim_experiment_2', to='network.Experiment'),
        ),
    ]
