"""
This file is a compatibility layer that imports settings from the main config.
It ensures backward compatibility with code that still imports from zignal.zignal.config.settings.
"""

# Show a warning message
import sys
print("WARNING: Using zignal/zignal/config/settings.py is deprecated. Update imports to use zignal.config.settings", file=sys.stderr)

# Import all settings from the consolidated settings
from zignal.config.settings import *
