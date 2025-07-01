#!/bin/bash

# Build and push Docker image to ECR for SageMaker Pipeline
# Usage: ./scripts/build_sagemaker_image.sh [region] [account-id] [image-name]

set -e

# Default values
REGION=${1:-us-east-1}
ACCOUNT_ID=${2:-$(aws sts get-caller-identity --query Account --output text)}
IMAGE_NAME=${3:-fantasy-football-2025}

# ECR repository name
REPO_NAME="${IMAGE_NAME}-pipeline"

echo "Building SageMaker Pipeline Docker image..."
echo "Region: $REGION"
echo "Account ID: $ACCOUNT_ID"
echo "Image name: $IMAGE_NAME"
echo "Repository: $REPO_NAME"

# Create ECR repository if it doesn't exist
aws ecr describe-repositories --repository-names $REPO_NAME --region $REGION 2>/dev/null || {
    echo "Creating ECR repository: $REPO_NAME"
    aws ecr create-repository --repository-name $REPO_NAME --region $REGION
}

# Get ECR login token
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Build Docker image
echo "Building Docker image..."
docker build -t $IMAGE_NAME .

# Tag image for ECR
ECR_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME"
docker tag $IMAGE_NAME:latest $ECR_URI:latest

# Push to ECR
echo "Pushing image to ECR..."
docker push $ECR_URI:latest

echo "✅ Image successfully pushed to ECR: $ECR_URI:latest"
echo ""
echo "You can now use this image in your SageMaker pipeline with:"
echo "Image URI: $ECR_URI:latest" 