#!/usr/bin/env python
"""
Script to remove the local .env file and ensure we only use the parent .env file
"""
import os
import sys
import shutil
from pathlib import Path

def remove_local_env():
    """Remove the local .env file and ensure we use only the parent .env file"""
    # Get paths to both .env files
    local_env_path = Path(__file__).resolve().parent / '.env'
    parent_env_path = Path(__file__).resolve().parent.parent / '.env'
    
    # Check if both files exist
    if not parent_env_path.exists():
        print(f"Error: Parent .env file not found at {parent_env_path}")
        print("Cannot proceed without a valid parent .env file.")
        return False
    
    if not local_env_path.exists():
        print(f"Local .env file not found at {local_env_path}")
        print("Nothing to remove.")
        return True
    
    # Create a backup of the local .env file first
    backup_path = local_env_path.with_name('.env_backup')
    
    try:
        if not backup_path.exists():
            shutil.copy2(local_env_path, backup_path)
            print(f"Created backup of local .env file at {backup_path}")
        
        # Remove the local .env file
        os.remove(local_env_path)
        print(f"Successfully removed local .env file at {local_env_path}")
        print(f"Now using only the parent .env file at {parent_env_path}")
        print("\nPlease restart your Django server for changes to take effect.")
        return True
    
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    if remove_local_env():
        print("Success! Now using only one .env file.")
    else:
        print("Failed to consolidate .env files.")
        sys.exit(1) 