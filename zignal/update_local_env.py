#!/usr/bin/env python
"""
Script to update the local .env file with the correct API key from the parent .env file
"""
import os
import re
from pathlib import Path

def update_local_env():
    """Update the local .env file with the API key from the parent .env file"""
    # Get paths to both .env files
    local_env_path = Path(__file__).resolve().parent / '.env'
    parent_env_path = Path(__file__).resolve().parent.parent / '.env'
    
    if not local_env_path.exists() or not parent_env_path.exists():
        print("Error: One or both .env files not found.")
        print(f"Local .env: {local_env_path.exists()}")
        print(f"Parent .env: {parent_env_path.exists()}")
        return False
    
    # Read the parent .env file to get the API key
    parent_env_content = parent_env_path.read_text()
    parent_api_key_match = re.search(r'^OPENAI_API_KEY=(.+)$', parent_env_content, re.MULTILINE)
    
    if not parent_api_key_match:
        print("Error: Could not find OPENAI_API_KEY in parent .env file.")
        return False
    
    parent_api_key = parent_api_key_match.group(1).strip()
    
    # Read the local .env file
    local_env_content = local_env_path.read_text()
    
    # Update the API key in the local .env file
    new_local_env_content = re.sub(
        r'^OPENAI_API_KEY=.+$',
        f'OPENAI_API_KEY={parent_api_key}',
        local_env_content,
        flags=re.MULTILINE
    )
    
    # Write the updated content back to the local .env file
    with open(local_env_path, 'w') as f:
        f.write(new_local_env_content)
    
    print(f"Updated local .env file with API key: {parent_api_key[:5]}***")
    print("Please restart your Django server for changes to take effect.")
    return True

if __name__ == "__main__":
    if update_local_env():
        print("Success! Local .env file has been updated.")
    else:
        print("Failed to update local .env file.") 