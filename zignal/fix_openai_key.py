#!/usr/bin/env python
"""
Script to check and update the OpenAI API key in the .env file
"""
import os
import sys
import re
from pathlib import Path

def check_env_file():
    """Check and update the .env file with a valid OpenAI API key"""
    # Get path to .env file (one directory up from current script)
    env_file_path = Path(__file__).resolve().parent.parent / '.env'
    
    if not env_file_path.exists():
        print(f"Error: .env file not found at {env_file_path}")
        print("Please create a .env file in your project root.")
        return False
    
    # Read the .env file
    with open(env_file_path, 'r') as f:
        env_content = f.read()
    
    # Check if OpenAI API key is already correctly set
    openai_key_match = re.search(r'^OPENAI_API_KEY=(.+)$', env_content, re.MULTILINE)
    
    if openai_key_match:
        current_key = openai_key_match.group(1).strip()
        if current_key and not current_key.startswith(('your_', '"your_', "'your_")) and len(current_key) > 20:
            print(f"OpenAI API key already set: {current_key[:5]}{'*' * 30}")
            return True
        else:
            print(f"Invalid OpenAI API key found: {current_key[:10]}...")
    else:
        print("OpenAI API key not found in .env file")
    
    # Ask for a new API key
    print("\nPlease enter your OpenAI API key (starts with 'sk-'):")
    new_key = input("> ").strip()
    
    if not new_key or not new_key.startswith('sk-') or len(new_key) < 20:
        print("Error: That doesn't look like a valid OpenAI API key")
        return False
    
    # Update or add the API key in the .env file
    if openai_key_match:
        # Replace existing key
        new_env_content = re.sub(
            r'^OPENAI_API_KEY=.+$',
            f'OPENAI_API_KEY={new_key}',
            env_content,
            flags=re.MULTILINE
        )
    else:
        # Add new key at the end of the file
        if env_content and not env_content.endswith('\n'):
            new_env_content = env_content + '\n'
        else:
            new_env_content = env_content
        new_env_content += f'OPENAI_API_KEY={new_key}\n'
    
    # Write the updated content back to the .env file
    with open(env_file_path, 'w') as f:
        f.write(new_env_content)
    
    print(f"OpenAI API key updated successfully: {new_key[:5]}{'*' * 30}")
    print("Please restart your Django development server for changes to take effect.")
    return True

if __name__ == "__main__":
    if check_env_file():
        print("\nSuccess! Your OpenAI API key has been updated.")
        print("Restart your Django server to apply the changes.")
    else:
        print("\nFailed to update OpenAI API key. Please try again.")
        sys.exit(1) 