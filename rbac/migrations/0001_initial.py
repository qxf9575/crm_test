# -*- coding: utf-8 -*-
# Generated by Django 1.11.11 on 2018-11-05 03:25
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Menu',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=32, unique=True, verbose_name='标题')),
                ('icon', models.CharField(blank=True, max_length=32, null=True, verbose_name='图标')),
                ('weight', models.IntegerField(default=1, verbose_name='权重')),
            ],
            options={
                'verbose_name': '菜单表',
                'verbose_name_plural': '菜单表',
            },
        ),
        migrations.CreateModel(
            name='Permission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=32, verbose_name='标题')),
                ('url', models.CharField(max_length=32, verbose_name='权限')),
                ('name', models.CharField(blank=True, max_length=32, null=True, unique=True, verbose_name='URL别名')),
                ('menu', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='rbac.Menu', verbose_name='菜单')),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='rbac.Permission', verbose_name='父权限')),
            ],
            options={
                'verbose_name': '权限表',
                'verbose_name_plural': '权限表',
            },
        ),
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=32, verbose_name='角色名称')),
                ('permissions', models.ManyToManyField(blank=True, to='rbac.Permission', verbose_name='角色所拥有的权限')),
            ],
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=32, verbose_name='用户名')),
                ('password', models.CharField(max_length=32, verbose_name='密码')),
                ('roles', models.ManyToManyField(blank=True, to='rbac.Role', verbose_name='用户所拥有的角色')),
            ],
        ),
    ]
