#!/bin/bash

# ===============================================
# 1. Configuration Variables
#    Update these with your specific values.
# ===============================================

# Replace with your AWS Account ID (e.g., 123456789012)
AWS_ACCOUNT_ID="857159677616" 

# Replace with your AWS Region (e.g., us-east-1)
AWS_REGION="us-east-2" 

# Replace with your ECR Repository Name
REPO_NAME="weasyprint-pdf"

# Define the local tag and ECR tag 
IMAGE_TAG="latest"

# Construct the full ECR URI
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
FULL_IMAGE_URI="${ECR_URI}/${REPO_NAME}:${IMAGE_TAG}"

# Stop script execution if any command fails
set -e

# ===============================================
# 2. Build the Docker Image
# ===============================================
echo "Building Docker image: ${REPO_NAME}:${IMAGE_TAG}..."
docker build -t ${REPO_NAME}:${IMAGE_TAG} .

# ===============================================
# 3. Authenticate Docker with ECR (Crucial Step for CloudShell)
# ===============================================
echo "Authenticating Docker with AWS ECR in region ${AWS_REGION}..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_URI}

# Check if authentication was successful
if [ $? -ne 0 ]; then
    echo "ERROR: Docker login failed. Check your AWS CLI configuration."
    exit 1
fi

# ===============================================
# 4. Tag and Push to ECR
# ===============================================
echo "Tagging image with full ECR URI: ${FULL_IMAGE_URI}"
docker tag ${REPO_NAME}:${IMAGE_TAG} ${FULL_IMAGE_URI}

echo "Pushing image to ECR..."
docker push ${FULL_IMAGE_URI}

echo "✅ Deployment successful! New image is now live on Lambda."

# Clean up local image tags to save disk space if desired
# docker rmi ${REPO_NAME}:${IMAGE_TAG}
# docker rmi ${FULL_IMAGE_URI}