# -*- coding: utf-8 -*-
# Generated by Django 1.11.11 on 2020-01-23 13:31
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_auto_20200121_0525'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='email_active',
            field=models.BooleanField(default=False, verbose_name='邮箱验证状态'),
        ),
    ]
