#!/bin/bash
set -e

# Configuration
# Replace these or set them as environment variables
PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project)}
REGION=${REGION:-"us-central1"}
SERVICE_NAME="tensoria"
API_IMAGE="gcr.io/${PROJECT_ID}/tensoria-api:latest"
BUCKET_NAME="${PROJECT_ID}-tensoria-models"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting deployment for ${SERVICE_NAME}...${NC}"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"

# 1. Enable APIs
echo -e "\n${YELLOW}1. Enabling required APIs...${NC}"
gcloud services enable artifactregistry.googleapis.com cloudbuild.googleapis.com run.googleapis.com

# 2. Create Bucket if not exists
echo -e "\n${YELLOW}2. Checking GCS Bucket...${NC}"
if ! gcloud storage buckets describe gs://${BUCKET_NAME} &>/dev/null; then
    echo "Creating bucket gs://${BUCKET_NAME}..."
    gcloud storage buckets create gs://${BUCKET_NAME} --location=${REGION}
else
    echo "Bucket gs://${BUCKET_NAME} already exists."
fi

# 3. Build API Image
echo -e "\n${YELLOW}3. Building API image...${NC}"
# Go to root directory
cd ..
gcloud builds submit --tag ${API_IMAGE} .
cd gcp

# 4. Generate Service YAML
echo -e "\n${YELLOW}4. Generating service configuration...${NC}"
if [ -z "$API_KEY" ]; then
    echo "Generating new API Key..."
    API_KEY="tensoria_$(openssl rand -base64 32 | tr -d '/+=')"
    echo -e "🔑 Generated API Key: ${GREEN}${API_KEY}${NC}"
    echo "SAVE THIS KEY! You will need it for your backend configuration."
fi

# Create deployed yaml from template
sed -e "s|\${PROJECT_ID}|${PROJECT_ID}|g" \
    -e "s|\${BUCKET_NAME}|${BUCKET_NAME}|g" \
    -e "s|\${API_KEY}|${API_KEY}|g" \
    service.yaml > service-deployed.yaml

# 5. Deploy to Cloud Run
echo -e "\n${YELLOW}5. Deploying to Cloud Run...${NC}"
gcloud run services replace service-deployed.yaml --region ${REGION}

# 6. Configure Permissions
echo -e "\n${YELLOW}6. Configuring permissions...${NC}"
# Get Service Account
SERVICE_ACCOUNT=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(spec.template.spec.serviceAccountName)')
if [ -z "$SERVICE_ACCOUNT" ]; then
    # Fallback to default compute account if not explicitly set
    NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")
    SERVICE_ACCOUNT="${NUMBER}-compute@developer.gserviceaccount.com"
fi

echo "Granting Storage Object Admin to ${SERVICE_ACCOUNT} on gs://${BUCKET_NAME}..."
gcloud storage buckets add-iam-policy-binding gs://${BUCKET_NAME} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/storage.objectAdmin"

echo -e "\n${GREEN}✅ Deployment Complete!${NC}"
echo -e "URL: $(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')"
echo -e "API Key: ${API_KEY}"
echo -e "\n⚠️  IMPORTANT: Don't forget to upload your models to gs://${BUCKET_NAME}/"
