# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-11-16 14:57
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0020_conference_is_meeting'),
    ]

    operations = [
        migrations.AlterField(
            model_name='conference',
            name='location',
            field=models.CharField(blank=True, max_length=2048, null=True),
        ),
    ]
