"""
DEPRECATED - This file is a temporary compatibility layer for transition.
All settings have been moved to zignal.config.settings.
"""

import os
import sys

# Display warning
import warnings
warnings.warn("Using zignal/zignal/config/settings.py is deprecated. Update imports to use zignal.config.settings", 
              DeprecationWarning, stacklevel=2)

# Force DEBUG to True for development
os.environ['DEBUG'] = 'True'

# Import the real settings
from zignal.config.settings import *

# Override critical settings to ensure things work during transition
DEBUG = True
ALLOWED_HOSTS = ['*'] 