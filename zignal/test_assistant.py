#!/usr/bin/env python
# Test script to verify OpenAI integration for the assistant feature

import os
import sys
import json
import openai

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zignal.zignal.config.settings')
import django
django.setup()

from django.conf import settings

# Verify API key is set
api_key = settings.OPENAI_API_KEY
if not api_key:
    print("Error: OPENAI_API_KEY is not set in settings")
    sys.exit(1)

# Set up OpenAI client
client = openai.OpenAI(api_key=api_key)

# Test connection by listing models
try:
    models = client.models.list()
    print("✅ OpenAI connection successful")
    print(f"Available models: {len(models.data)}")
    
    for model in models.data[:5]:  # Print first 5 models
        print(f"- {model.id}")
    
    if len(models.data) > 5:
        print(f"... and {len(models.data) - 5} more")
        
except Exception as e:
    print(f"❌ Error connecting to OpenAI: {str(e)}")
    sys.exit(1)

# Create a test assistant
try:
    assistant = client.beta.assistants.create(
        name="Test Assistant",
        instructions="You are a test assistant to verify that the OpenAI API is working properly.",
        model=settings.OPENAI_MODEL,
    )
    print(f"\n✅ Successfully created test assistant with ID: {assistant.id}")
    
    # Clean up by deleting the test assistant
    client.beta.assistants.delete(assistant.id)
    print(f"✅ Successfully deleted test assistant")
    
except Exception as e:
    print(f"❌ Error creating/deleting assistant: {str(e)}")
    sys.exit(1)

print("\n✅ All tests passed!") 