# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-06-28 16:25
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('typer', '0012_auto_20170623_1912'),
    ]

    operations = [
        migrations.CreateModel(
            name='Votes',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('votes', models.SmallIntegerField(blank=True, default=None, null=True)),
                ('game', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='typer.Game')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='typer.Group')),
            ],
        ),
        migrations.RemoveField(
            model_name='groupgame',
            name='game',
        ),
        migrations.RemoveField(
            model_name='groupgame',
            name='group',
        ),
        migrations.AddField(
            model_name='bonusround',
            name='round',
            field=models.PositiveSmallIntegerField(blank=True, default=None, null=True),
        ),
        migrations.DeleteModel(
            name='GroupGame',
        ),
    ]
