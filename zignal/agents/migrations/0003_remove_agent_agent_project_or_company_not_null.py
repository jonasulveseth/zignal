"""
Empty migration since the constraint was removed from migration 0002
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('agents', '0002_agent_company_agent_project_and_more'),
    ]

    operations = [
        # No operations needed
    ]
