# Generated by Django 5.2 on 2025-04-19 12:34

import datasilo.models
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('companies', '0001_initial'),
        ('projects', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DataSilo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('slug', models.SlugField(blank=True, max_length=255, unique=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='data_silos', to='companies.company')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_silos', to=settings.AUTH_USER_MODEL)),
                ('project', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='data_silos', to='projects.project')),
            ],
            options={
                'verbose_name': 'Data Silo',
                'verbose_name_plural': 'Data Silos',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='DataFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('file', models.FileField(upload_to=datasilo.models.file_upload_path)),
                ('file_type', models.CharField(choices=[('document', 'Document'), ('image', 'Image'), ('spreadsheet', 'Spreadsheet'), ('presentation', 'Presentation'), ('code', 'Code'), ('audio', 'Audio'), ('video', 'Video'), ('other', 'Other')], default='document', max_length=20)),
                ('content_type', models.CharField(blank=True, max_length=255, null=True)),
                ('size', models.BigIntegerField(default=0)),
                ('status', models.CharField(choices=[('pending', 'Pending Processing'), ('processing', 'Processing'), ('processed', 'Processed'), ('failed', 'Failed Processing')], default='pending', max_length=20)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('embedding_available', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='files', to='companies.company')),
                ('project', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='files', to='projects.project')),
                ('uploaded_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='uploaded_files', to=settings.AUTH_USER_MODEL)),
                ('data_silo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='files', to='datasilo.datasilo')),
            ],
            options={
                'verbose_name': 'Data File',
                'verbose_name_plural': 'Data Files',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='datasilo',
            constraint=models.CheckConstraint(condition=models.Q(('project__isnull', False), ('company__isnull', False), _connector='OR'), name='project_or_company_not_null'),
        ),
        migrations.AddConstraint(
            model_name='datasilo',
            constraint=models.UniqueConstraint(fields=('name', 'project'), name='unique_name_per_project'),
        ),
        migrations.AddConstraint(
            model_name='datasilo',
            constraint=models.UniqueConstraint(fields=('name', 'company'), name='unique_name_per_company'),
        ),
    ]
