# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-06-16 19:19
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('typer', '0004_auto_20170616_2034'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='league',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='typer.League'),
        ),
    ]