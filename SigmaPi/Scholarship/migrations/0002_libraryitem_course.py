# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-04-03 13:36
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Scholarship', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='libraryitem',
            name='course',
            field=models.CharField(default=b'', max_length=10),
        ),
    ]
