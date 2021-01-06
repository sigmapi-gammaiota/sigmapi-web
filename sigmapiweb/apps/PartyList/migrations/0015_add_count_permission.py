# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-03-29 20:30
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('PartyList', '0014_change_guest_listings'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='party',
            options={'permissions': (('manage_parties', 'Can manage Parties'), ('can_modify_count', 'Can modify guest count')), 'verbose_name': 'Party', 'verbose_name_plural': 'Parties'},
        ),
    ]