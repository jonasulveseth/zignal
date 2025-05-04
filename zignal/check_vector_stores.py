#!/usr/bin/env python
"""
Script to check if vector stores are supported in the OpenAI SDK
"""
import os
import sys
import json
import django

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zignal.config.settings')
django.setup()

from django.conf import settings
from openai import OpenAI
import logging
from companies.models import Company

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_vector_stores():
    """Check if vector stores are supported in the OpenAI SDK"""
    print("\n=== OpenAI SDK Vector Stores Check ===\n")
    
    # Get OpenAI module version
    import openai
    print(f"OpenAI module version: {openai.__version__}")
    
    # Initialize the client
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    # Check if beta namespace is available
    print(f"Client has beta namespace: {hasattr(client, 'beta')}")
    if hasattr(client, 'beta'):
        # List beta attributes
        beta_attrs = [attr for attr in dir(client.beta) if not attr.startswith('_')]
        print(f"Beta attributes: {beta_attrs}")
        
        # Check for vector_stores specifically
        has_vector_stores = hasattr(client.beta, 'vector_stores')
        print(f"Beta has vector_stores: {has_vector_stores}")
        
        if has_vector_stores:
            # List vector_stores attributes
            try:
                vs_attrs = [attr for attr in dir(client.beta.vector_stores) if not attr.startswith('_')]
                print(f"Vector stores attributes: {vs_attrs}")
                print("\nVector stores are supported in this version of the OpenAI SDK!")
            except Exception as e:
                print(f"Error accessing vector_stores attributes: {e}")
        else:
            print("\nVector stores are NOT supported in this version of the OpenAI SDK.")
    else:
        print("Beta namespace not available in this version of the OpenAI SDK.")
    
    print("\n=== Check Complete ===\n")

if __name__ == "__main__":
    check_vector_stores() 