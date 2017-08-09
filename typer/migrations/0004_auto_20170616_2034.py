# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-06-16 18:34
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('typer', '0003_game_round'),
    ]

    operations = [
        migrations.AlterField(
            model_name='game',
            name='score_away',
            field=models.PositiveSmallIntegerField(null=True),
        ),
        migrations.AlterField(
            model_name='game',
            name='score_home',
            field=models.PositiveSmallIntegerField(null=True),
        ),
    ]
