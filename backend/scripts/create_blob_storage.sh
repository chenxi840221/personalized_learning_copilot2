#!/bin/bash
# Script to create Azure Blob Storage resources using Azure CLI
# Usage: ./create_blob_storage.sh <resource-group> <storage-account-name> <location>

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "Azure CLI is not installed. Please install it first:"
    echo "https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if logged in to Azure
az account show &> /dev/null
if [ $? -ne 0 ]; then
    echo "Not logged in to Azure. Running 'az login'..."
    az login
fi

# Check arguments
if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <resource-group> <storage-account-name> [location]"
    echo "Example: $0 learning-copilot-rg learningcopilotstore eastus"
    exit 1
fi

RESOURCE_GROUP=$1
STORAGE_ACCOUNT_NAME=$2
LOCATION=${3:-eastus}  # Default to eastus if not provided

# Create resource group if it doesn't exist
echo "Checking if resource group $RESOURCE_GROUP exists..."
if ! az group show --name "$RESOURCE_GROUP" &> /dev/null; then
    echo "Creating resource group $RESOURCE_GROUP in $LOCATION..."
    az group create --name "$RESOURCE_GROUP" --location "$LOCATION"
else
    echo "Resource group $RESOURCE_GROUP already exists"
fi

# Create storage account
echo "Creating storage account $STORAGE_ACCOUNT_NAME..."
if ! az storage account show --name "$STORAGE_ACCOUNT_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
    az storage account create \
        --name "$STORAGE_ACCOUNT_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --location "$LOCATION" \
        --sku Standard_LRS \
        --kind StorageV2 \
        --https-only true \
        --min-tls-version TLS1_2
    echo "Storage account $STORAGE_ACCOUNT_NAME created successfully"
else
    echo "Storage account $STORAGE_ACCOUNT_NAME already exists"
fi

# Get storage account key and connection string
echo "Retrieving storage account connection string..."
CONNECTION_STRING=$(az storage account show-connection-string \
    --name "$STORAGE_ACCOUNT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --output tsv)

# Set environment variable for future commands in this script
export AZURE_STORAGE_CONNECTION_STRING="$CONNECTION_STRING"

# Create containers
CONTAINERS=("student-reports" "learning-materials" "profile-images")

for CONTAINER in "${CONTAINERS[@]}"; do
    echo "Creating container $CONTAINER..."
    az storage container create --name "$CONTAINER" --public-access off
done

# Print connection string info
echo ""
echo "================================================================================"
echo "STORAGE ACCOUNT CREATED SUCCESSFULLY"
echo "================================================================================"
echo ""
echo "Connection String:"
echo "$CONNECTION_STRING"
echo ""
echo "To use this connection string, add it to your environment variables:"
echo ""
echo "Linux/Mac:"
echo "export AZURE_STORAGE_CONNECTION_STRING=\"$CONNECTION_STRING\""
echo ""
echo "Windows Command Prompt:"
echo "set AZURE_STORAGE_CONNECTION_STRING=\"$CONNECTION_STRING\""
echo ""
echo "Windows PowerShell:"
echo "\$env:AZURE_STORAGE_CONNECTION_STRING=\"$CONNECTION_STRING\""
echo ""
echo "Or add it to your .env file or settings.py file"