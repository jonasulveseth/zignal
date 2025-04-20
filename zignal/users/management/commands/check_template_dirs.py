from django.core.management.base import BaseCommand
from django.conf import settings
import os

class Command(BaseCommand):
    help = 'Check template directories and socialaccount app installation'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Checking template directories...'))
        
        # Check template directories
        template_dirs = []
        for template_config in settings.TEMPLATES:
            if 'DIRS' in template_config:
                template_dirs.extend(template_config['DIRS'])
        
        self.stdout.write(f"Template directories: {template_dirs}")
        
        # Check socialaccount in installed apps
        if 'allauth.socialaccount' in settings.INSTALLED_APPS:
            self.stdout.write(self.style.SUCCESS("allauth.socialaccount is in INSTALLED_APPS"))
        else:
            self.stdout.write(self.style.ERROR("allauth.socialaccount is NOT in INSTALLED_APPS"))
        
        # Check if socialaccount template tag directory exists
        import allauth
        allauth_path = os.path.dirname(allauth.__file__)
        socialaccount_templatetags_path = os.path.join(allauth_path, 'socialaccount', 'templatetags')
        
        if os.path.exists(socialaccount_templatetags_path):
            self.stdout.write(self.style.SUCCESS(f"socialaccount templatetags directory exists at: {socialaccount_templatetags_path}"))
            # List files in templatetags directory
            files = os.listdir(socialaccount_templatetags_path)
            self.stdout.write(f"Files in templatetags directory: {files}")
        else:
            self.stdout.write(self.style.ERROR(f"socialaccount templatetags directory does NOT exist at: {socialaccount_templatetags_path}")) 