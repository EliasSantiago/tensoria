#!/bin/bash
set -e

# Configuration
PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project)}
REGION=${REGION:-"us-central1"}
BUCKET_NAME="${PROJECT_ID}-tensoria-models"
JOB_NAME="tensoria-pull-model"

if [ -z "$1" ]; then
    echo "Usage: ./pull_model.sh <model_name>"
    echo "Example: ./pull_model.sh mistral"
    echo "Example: ./pull_model.sh deepseek-coder:6.7b"
    exit 1
fi

MODEL_NAME=$1

echo "🚀 Preparing to pull model '${MODEL_NAME}' to bucket gs://${BUCKET_NAME}..."

# Get Service Account used by the main service
SERVICE_ACCOUNT=$(gcloud run services describe tensoria --region ${REGION} --format 'value(spec.template.spec.serviceAccountName)')
if [ -z "$SERVICE_ACCOUNT" ]; then
    echo "Error: Could not find service account for 'tensoria' service."
    echo "Make sure you deployed the main service first using ./deploy.sh"
    exit 1
fi

# Generate Job YAML
sed -e "s|\${BUCKET_NAME}|${BUCKET_NAME}|g" \
    -e "s|\${SERVICE_ACCOUNT}|${SERVICE_ACCOUNT}|g" \
    job-pull.yaml > job-pull-deployed.yaml

# Deploy Job (update if exists)
echo "Deploying Cloud Run Job..."
gcloud run jobs replace job-pull-deployed.yaml --region ${REGION}

# Execute Job
echo "Executing Job to pull '${MODEL_NAME}'..."
echo "This may take a few minutes depending on model size..."
gcloud run jobs execute ${JOB_NAME} \
    --region ${REGION} \
    --update-env-vars MODEL_NAME=${MODEL_NAME} \
    --wait

echo "✅ Model '${MODEL_NAME}' pulled successfully!"
