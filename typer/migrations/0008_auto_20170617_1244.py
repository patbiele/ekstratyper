# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-06-17 10:44
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('typer', '0007_auto_20170617_1237'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='alias',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
