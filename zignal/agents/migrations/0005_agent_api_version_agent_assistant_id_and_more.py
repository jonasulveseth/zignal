# Generated by Django 5.2 on 2025-04-22 11:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agents', '0004_meetingtranscript'),
    ]

    operations = [
        migrations.AddField(
            model_name='agent',
            name='api_version',
            field=models.CharField(choices=[('chat_completion', 'Chat Completion API'), ('assistants', 'Assistants API')], default='chat_completion', max_length=20),
        ),
        migrations.AddField(
            model_name='agent',
            name='assistant_id',
            field=models.CharField(blank=True, help_text='OpenAI Assistant ID (only used with Assistants API)', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='conversation',
            name='thread_id',
            field=models.CharField(blank=True, help_text='OpenAI Thread ID (only used with Assistants API)', max_length=255, null=True),
        ),
    ]
