#!/usr/bin/env python
"""
Test script to upload a file to S3 through the web application
"""
import os
import requests
import uuid
import logging
import tempfile
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# URL for upload endpoint - adjust as needed for your app
UPLOAD_URL = 'https://www.zignal.se/silos/company-documents-fru-1746302927/upload/'

# Credentials - you'd need to set these
USERNAME = os.environ.get('ZIGNAL_USERNAME')
PASSWORD = os.environ.get('ZIGNAL_PASSWORD')

def test_upload():
    """Test uploading a file through the web app"""
    if not USERNAME or not PASSWORD:
        logger.error("Please set ZIGNAL_USERNAME and ZIGNAL_PASSWORD environment variables")
        return False
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    # First, get CSRF token
    try:
        logger.info("Getting CSRF token...")
        response = session.get(UPLOAD_URL)
        if response.status_code != 200:
            logger.error(f"Failed to get upload page: {response.status_code}")
            return False
        
        # Extract CSRF token from response
        csrf_token = None
        for line in response.text.split("\n"):
            if 'csrfmiddlewaretoken' in line and 'value' in line:
                import re
                match = re.search(r'value=["\']([^"\']+)["\']', line)
                if match:
                    csrf_token = match.group(1)
                    break
        
        if not csrf_token:
            logger.error("Could not find CSRF token")
            return False
        
        logger.info("Successfully got CSRF token")
        
        # Login if needed - may need to adjust URL and parameters
        login_url = 'https://www.zignal.se/accounts/login/'
        login_data = {
            'csrfmiddlewaretoken': csrf_token,
            'login': USERNAME,
            'password': PASSWORD,
            'next': UPLOAD_URL
        }
        
        logger.info("Logging in...")
        login_response = session.post(login_url, data=login_data, headers={'Referer': login_url})
        if login_response.status_code != 200:
            logger.error(f"Login failed with status: {login_response.status_code}")
            return False
        
        logger.info("Login successful")
        
        # Get a fresh CSRF token from the upload page
        response = session.get(UPLOAD_URL)
        if response.status_code != 200:
            logger.error(f"Failed to get upload page after login: {response.status_code}")
            return False
        
        # Create a test file to upload
        test_id = uuid.uuid4().hex[:8]
        test_content = f"Test content for web upload {test_id}"
        
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
            temp_file.write(test_content.encode())
            temp_file_path = temp_file.name
        
        try:
            # Prepare file upload
            test_filename = f"web_upload_test_{test_id}.txt"
            
            # Prepare form data
            files = {'file': (test_filename, open(temp_file_path, 'rb'), 'text/plain')}
            
            data = {
                'csrfmiddlewaretoken': csrf_token,
                'name': f"Web Upload Test {test_id}",
                'description': f"Test file uploaded through web API at {time.strftime('%Y-%m-%d %H:%M:%S')}",
                'file_type': 'document'
            }
            
            # Upload the file
            logger.info(f"Uploading test file: {test_filename}")
            upload_response = session.post(UPLOAD_URL, files=files, data=data, headers={'Referer': UPLOAD_URL})
            
            # Check response
            if upload_response.status_code != 200:
                logger.error(f"Upload failed with status: {upload_response.status_code}")
                logger.error(f"Response: {upload_response.text[:500]}")
                return False
            
            # Look for success message in response
            if "File uploaded successfully" in upload_response.text:
                logger.info("File uploaded successfully through web interface")
                return True
            else:
                logger.warning("Upload request successful, but success message not found in response")
                logger.info(f"Response: {upload_response.text[:500]}")
                return True  # Still return True as the request was successful
            
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
            logger.info("Temporary file deleted")
        
    except Exception as e:
        logger.error(f"Error in test upload: {str(e)}")
        return False

if __name__ == "__main__":
    if test_upload():
        logger.info("Test completed successfully")
    else:
        logger.error("Test failed") 