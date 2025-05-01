#!/usr/bin/env python
"""
Simple script to check OpenAI SDK vector stores directly
"""
import os
from openai import OpenAI

# Get the API key from environment or prompt
api_key = os.environ.get("OPENAI_API_KEY") or input("Enter your OpenAI API key: ")

# Initialize the client
client = OpenAI(api_key=api_key)

# Print OpenAI version
import openai
print(f"OpenAI version: {openai.__version__}")

# Check for vector_stores on the client
print(f"Client has vector_stores: {hasattr(client, 'vector_stores')}")

if hasattr(client, 'vector_stores'):
    try:
        # List methods of vector_stores
        vs_attrs = [attr for attr in dir(client.vector_stores) if not attr.startswith('_')]
        print(f"Vector stores methods: {vs_attrs}")
        
        # Try to list vector stores
        print("\nTrying to list vector stores...")
        vector_stores = client.vector_stores.list()
        print(f"Vector stores list: {vector_stores}")
    except Exception as e:
        print(f"Error using vector_stores: {str(e)}")
        
    # Try to create a vector store
    try:
        print("\nTrying to create a vector store...")
        vector_store = client.vector_stores.create(
            name="Test Vector Store"
        )
        print(f"Created vector store: {vector_store.id}")
    except Exception as e:
        print(f"Error creating vector store: {str(e)}")
else:
    print("vector_stores not available on client") 