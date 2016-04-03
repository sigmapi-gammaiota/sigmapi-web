# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-04-03 13:36
from __future__ import unicode_literals

import Archive.models
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Bylaws',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('filepath', models.FileField(upload_to=Archive.models.bylaws_path)),
            ],
            options={
                'verbose_name': 'Bylaws',
                'verbose_name_plural': 'Bylaws',
                'permissions': (('access_bylaws', 'Can access bylaws.'),),
            },
        ),
        migrations.CreateModel(
            name='Guide',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('datePosted', models.DateField()),
                ('description', models.TextField(blank=True)),
                ('filepath', models.FileField(upload_to=Archive.models.guidepath)),
                ('path', models.SlugField(max_length=15)),
            ],
            options={
                'verbose_name': 'Guide',
                'verbose_name_plural': 'Guides',
                'permissions': (('access_guide', 'Can access guides.'),),
            },
        ),
        migrations.CreateModel(
            name='HouseRules',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('filepath', models.FileField(upload_to=Archive.models.houserules_path)),
            ],
            options={
                'verbose_name': 'House Rules',
                'verbose_name_plural': 'House Rules',
                'permissions': (('access_houserules', 'Can access house rules.'),),
            },
        ),
    ]
