# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2018-03-14 17:18
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('network', '0014_auto_20180309_1027'),
    ]

    operations = [
        migrations.AddField(
            model_name='metadatarec',
            name='personal_experiment',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='metadatarec_owned', to='network.Experiment'),
        ),
        migrations.AddField(
            model_name='primarydatarec',
            name='dataset',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='primarydatarec_recommended', to='network.Dataset'),
        ),
        migrations.AddField(
            model_name='primarydatarec',
            name='personal_dataset',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='primarydatarec_owned', to='network.Dataset'),
        ),
        migrations.AddField(
            model_name='primarydatarec',
            name='personal_experiment',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='primarydatarec_owned', to='network.Experiment'),
        ),
        migrations.AlterField(
            model_name='metadatarec',
            name='experiment',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='metadatarec_recommended', to='network.Experiment'),
        ),
        migrations.AlterField(
            model_name='primarydatarec',
            name='experiment',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='primarydatarec_recommended', to='network.Experiment'),
        ),
    ]
