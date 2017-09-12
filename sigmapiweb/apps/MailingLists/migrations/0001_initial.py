# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-09-12 14:16
from __future__ import unicode_literals

import common.mixins
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('auth', '0008_alter_user_username_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='MailingList',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=16, unique=True)),
                ('description', models.CharField(default='', max_length=128)),
            ],
            bases=(common.mixins.ModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name='MailingListAccess',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('can_send', models.BooleanField(default=False)),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='auth.Group')),
                ('mailing_list', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='MailingLists.MailingList')),
            ],
            bases=(common.mixins.ModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name='MailingListSubscription',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mailing_list', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='MailingLists.MailingList')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            bases=(common.mixins.ModelMixin, models.Model),
        ),
        migrations.AlterUniqueTogether(
            name='mailinglistsubscription',
            unique_together=set([('mailing_list', 'user')]),
        ),
        migrations.AlterUniqueTogether(
            name='mailinglistaccess',
            unique_together=set([('mailing_list', 'group')]),
        ),
    ]