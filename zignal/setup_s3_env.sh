#!/bin/bash
# Script to set up AWS environment variables for S3 storage

# Text colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== S3 Environment Setup ===${NC}"
echo "This script will help you set up the AWS environment variables for S3 storage."

# Create or update .env file
ENV_FILE=".env"

# Check if .env file exists
if [ -f "$ENV_FILE" ]; then
    echo -e "${GREEN}Found existing .env file${NC}"
    echo "Would you like to update it? (y/n)"
    read -r update_env
    if [[ "$update_env" != "y" ]]; then
        echo "Exiting without changes."
        exit 0
    fi
fi

# Get AWS credentials from user
echo
echo -e "${BLUE}Enter your AWS credentials:${NC}"
echo -n "AWS Access Key ID: "
read -r aws_access_key
echo -n "AWS Secret Access Key: "
read -r aws_secret_key
echo -n "AWS S3 Bucket Name (default: zignalse): "
read -r aws_bucket_name
aws_bucket_name=${aws_bucket_name:-zignalse}
echo -n "AWS Region (default: eu-west-1): "
read -r aws_region
aws_region=${aws_region:-eu-west-1}
echo -n "AWS Location prefix (default: media): "
read -r aws_location
aws_location=${aws_location:-media}

# Add or update .env file
if [ -f "$ENV_FILE" ]; then
    # Back up existing file
    cp "$ENV_FILE" "${ENV_FILE}.bak"
    echo -e "${GREEN}Backed up existing .env to ${ENV_FILE}.bak${NC}"
    
    # Update AWS settings
    if grep -q "AWS_ACCESS_KEY_ID" "$ENV_FILE"; then
        sed -i '' "s/^AWS_ACCESS_KEY_ID=.*/AWS_ACCESS_KEY_ID=$aws_access_key/" "$ENV_FILE"
    else
        echo "AWS_ACCESS_KEY_ID=$aws_access_key" >> "$ENV_FILE"
    fi
    
    if grep -q "AWS_SECRET_ACCESS_KEY" "$ENV_FILE"; then
        sed -i '' "s/^AWS_SECRET_ACCESS_KEY=.*/AWS_SECRET_ACCESS_KEY=$aws_secret_key/" "$ENV_FILE"
    else
        echo "AWS_SECRET_ACCESS_KEY=$aws_secret_key" >> "$ENV_FILE"
    fi
    
    if grep -q "AWS_STORAGE_BUCKET_NAME" "$ENV_FILE"; then
        sed -i '' "s/^AWS_STORAGE_BUCKET_NAME=.*/AWS_STORAGE_BUCKET_NAME=$aws_bucket_name/" "$ENV_FILE"
    else
        echo "AWS_STORAGE_BUCKET_NAME=$aws_bucket_name" >> "$ENV_FILE"
    fi
    
    if grep -q "AWS_S3_REGION_NAME" "$ENV_FILE"; then
        sed -i '' "s/^AWS_S3_REGION_NAME=.*/AWS_S3_REGION_NAME=$aws_region/" "$ENV_FILE"
    else
        echo "AWS_S3_REGION_NAME=$aws_region" >> "$ENV_FILE"
    fi
    
    if grep -q "AWS_LOCATION" "$ENV_FILE"; then
        sed -i '' "s/^AWS_LOCATION=.*/AWS_LOCATION=$aws_location/" "$ENV_FILE"
    else
        echo "AWS_LOCATION=$aws_location" >> "$ENV_FILE"
    fi
    
    if grep -q "USE_S3_STORAGE" "$ENV_FILE"; then
        sed -i '' "s/^USE_S3_STORAGE=.*/USE_S3_STORAGE=True/" "$ENV_FILE"
    else
        echo "USE_S3_STORAGE=True" >> "$ENV_FILE"
    fi
else
    # Create new .env file
    cat > "$ENV_FILE" << EOF
# AWS S3 configuration
AWS_ACCESS_KEY_ID=$aws_access_key
AWS_SECRET_ACCESS_KEY=$aws_secret_key
AWS_STORAGE_BUCKET_NAME=$aws_bucket_name
AWS_S3_REGION_NAME=$aws_region
AWS_LOCATION=$aws_location

# Django settings
DEBUG=True
SECRET_KEY=django-insecure-mcc@@y*qg7%42w)mw44s=((ukn@e7$!!*5af1+f7xvtlz(t7i%
ALLOWED_HOSTS=*

# Set to True to force S3 storage even in development
USE_S3_STORAGE=True
EOF
    echo -e "${GREEN}Created new .env file${NC}"
fi

echo
echo -e "${GREEN}=== Environment variables set up successfully! ===${NC}"
echo "To use these settings in your current shell, run:"
echo -e "${BLUE}source .env${NC}"
echo
echo "You can test your S3 configuration by running:"
echo -e "${BLUE}python zignal/test_s3_connection.py${NC}"
echo
echo "Once everything is working, restart your Django server:"
echo -e "${BLUE}python zignal/manage.py runserver${NC}" 