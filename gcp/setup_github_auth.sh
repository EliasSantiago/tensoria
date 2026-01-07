#!/bin/bash
set -e

# Configuration
PROJECT_ID=$(gcloud config get-value project)
GITHUB_REPO="EliasSantiago/tensoria" # CHANGE THIS to your username/repo
SERVICE_ACCOUNT_NAME="github-actions-deployer"
WORKLOAD_IDENTITY_POOL="github-pool-actions" # Changed name to avoid soft-delete conflict
WORKLOAD_IDENTITY_PROVIDER="github-provider"

echo "🚀 Setting up Workload Identity Federation for repo: ${GITHUB_REPO}"
echo "Project: ${PROJECT_ID}"

# ... (skip enabling APIs as they are likely enabled) ...

# 4. Create Workload Identity Pool
if ! gcloud iam workload-identity-pools describe ${WORKLOAD_IDENTITY_POOL} --location="global" &>/dev/null; then
    gcloud iam workload-identity-pools create ${WORKLOAD_IDENTITY_POOL} \
        --location="global" \
        --display-name="GitHub Actions Pool"
    echo "Created Pool: ${WORKLOAD_IDENTITY_POOL}"
elif gcloud iam workload-identity-pools describe ${WORKLOAD_IDENTITY_POOL} --location="global" --format="value(state)" | grep -q "DELETED"; then
    echo "Pool ${WORKLOAD_IDENTITY_POOL} is deleted. Undeleting..."
    gcloud iam workload-identity-pools undelete ${WORKLOAD_IDENTITY_POOL} --location="global"
else
    echo "Pool ${WORKLOAD_IDENTITY_POOL} already exists."
fi

# 5. Create Provider
if ! gcloud iam workload-identity-pools providers describe ${WORKLOAD_IDENTITY_PROVIDER} \
    --location="global" \
    --workload-identity-pool=${WORKLOAD_IDENTITY_POOL} &>/dev/null; then
    
    echo "Creating Provider ${WORKLOAD_IDENTITY_PROVIDER}..."
    gcloud iam workload-identity-pools providers create-oidc ${WORKLOAD_IDENTITY_PROVIDER} \
        --location="global" \
        --workload-identity-pool=${WORKLOAD_IDENTITY_POOL} \
        --display-name="GitHub Provider" \
        --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
        --attribute-condition="assertion.repository == '${GITHUB_REPO}'" \
        --issuer-uri="https://token.actions.githubusercontent.com"
else
    echo "Provider ${WORKLOAD_IDENTITY_PROVIDER} already exists. Updating..."
    gcloud iam workload-identity-pools providers update-oidc ${WORKLOAD_IDENTITY_PROVIDER} \
        --location="global" \
        --workload-identity-pool=${WORKLOAD_IDENTITY_POOL} \
        --display-name="GitHub Provider" \
        --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
        --attribute-condition="assertion.repository == '${GITHUB_REPO}'" \
        --issuer-uri="https://token.actions.githubusercontent.com"
fi

# 6. Allow GitHub Repo to impersonate Service Account
# IMPORTANT: This binds specifically to your repo
gcloud iam service-accounts add-iam-policy-binding "${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --project="${PROJECT_ID}" \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/projects/$(gcloud projects describe ${PROJECT_ID} --format='value(projectNumber)')/locations/global/workloadIdentityPools/${WORKLOAD_IDENTITY_POOL}/attribute.repository/${GITHUB_REPO}"

# 7. Output Secrets for GitHub
PROVIDER_ID=$(gcloud iam workload-identity-pools providers describe ${WORKLOAD_IDENTITY_PROVIDER} \
    --location="global" \
    --workload-identity-pool=${WORKLOAD_IDENTITY_POOL} \
    --format="value(name)")

echo ""
echo "✅ Setup Complete!"
echo "====================================================="
echo "Go to your GitHub Repo -> Settings -> Secrets and variables -> Actions"
echo "Add the following secrets:"
echo ""
echo "GCP_PROJECT_ID: ${PROJECT_ID}"
echo "GCP_SERVICE_ACCOUNT: ${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
echo "GCP_WORKLOAD_IDENTITY_PROVIDER: ${PROVIDER_ID}"
echo "TENSORIA_API_KEY: (Your generated API Key)"
echo "====================================================="
