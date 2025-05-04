#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    # Add the parent directory to Python path for proper imports
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Set up Django settings module
    settings_module = 'zignal.config.settings'
    print(f"Setting DJANGO_SETTINGS_MODULE to: {settings_module}")
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    
    # Print Python path for debugging
    print(f"Python path: {sys.path}")
    
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
