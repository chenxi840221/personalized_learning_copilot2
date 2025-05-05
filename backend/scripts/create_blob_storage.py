#!/usr/bin/env python
"""
Script to create Azure Blob Storage resources for the personalized learning copilot.
This creates a storage account and needed containers, then outputs the connection string.

Usage:
    python create_blob_storage.py --resource-group <resource-group> --location <location> --name <storage-account-name>

Requirements:
    pip install azure-identity azure-mgmt-resource azure-mgmt-storage azure-storage-blob
"""

import argparse
import os
import sys
import time
from azure.identity import DefaultAzureCredential, AzureCliCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.core.exceptions import ResourceExistsError, ClientAuthenticationError
from azure.storage.blob import BlobServiceClient

def create_resource_group(resource_client, resource_group_name, location):
    """Create resource group if it doesn't exist"""
    print(f"Checking if resource group {resource_group_name} exists...")
    groups = resource_client.resource_groups.list()
    for group in groups:
        if group.name == resource_group_name:
            print(f"Resource group {resource_group_name} already exists in location {group.location}")
            return
    
    print(f"Creating resource group {resource_group_name} in {location}...")
    resource_client.resource_groups.create_or_update(
        resource_group_name,
        {"location": location}
    )
    print(f"Resource group {resource_group_name} created successfully")

def create_storage_account(storage_client, resource_group_name, storage_account_name, location):
    """Create a storage account"""
    print(f"Creating storage account {storage_account_name}...")
    try:
        poller = storage_client.storage_accounts.begin_create(
            resource_group_name,
            storage_account_name,
            {
                "location": location,
                "kind": "StorageV2",
                "sku": {"name": "Standard_LRS"},
                "enable_https_traffic_only": True,
                "minimum_tls_version": "TLS1_2",
                "encryption": {
                    "services": {
                        "file": {"key_type": "Account", "enabled": True},
                        "blob": {"key_type": "Account", "enabled": True}
                    },
                    "key_source": "Microsoft.Storage"
                }
            }
        )
        # Wait for the operation to complete
        storage_account = poller.result()
        print(f"Storage account {storage_account_name} created successfully")
        return storage_account
    except ResourceExistsError:
        print(f"Storage account {storage_account_name} already exists")
        return storage_client.storage_accounts.get_properties(
            resource_group_name, 
            storage_account_name
        )

def get_storage_connection_string(storage_client, resource_group_name, storage_account_name):
    """Get storage account connection string"""
    print("Retrieving storage account keys...")
    keys = storage_client.storage_accounts.list_keys(
        resource_group_name, 
        storage_account_name
    )
    
    conn_string = f"DefaultEndpointsProtocol=https;AccountName={storage_account_name};AccountKey={keys.keys[0].value};EndpointSuffix=core.windows.net"
    return conn_string

def create_containers(connection_string):
    """Create required containers"""
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    
    containers = [
        "student-reports",
        "learning-materials",
        "profile-images"
    ]
    
    for container_name in containers:
        try:
            print(f"Creating container {container_name}...")
            blob_service_client.create_container(container_name)
            print(f"Container {container_name} created successfully")
        except ResourceExistsError:
            print(f"Container {container_name} already exists")

def main():
    parser = argparse.ArgumentParser(description='Create Azure Blob Storage resources')
    parser.add_argument('--resource-group', required=True, help='Azure resource group name')
    parser.add_argument('--location', default='eastus', help='Azure region (default: eastus)')
    parser.add_argument('--name', required=True, help='Storage account name (must be globally unique)')
    
    args = parser.parse_args()
    
    # Storage account names must be between 3 and 24 characters in length and may contain 
    # numbers and lowercase letters only
    if not args.name.islower() or not args.name.isalnum() or len(args.name) < 3 or len(args.name) > 24:
        print("Error: Storage account name must be 3-24 lowercase alphanumeric characters")
        sys.exit(1)
    
    try:
        print("Authenticating with Azure...")
        try:
            # Try CLI credential first
            credential = AzureCliCredential()
            # Test the credential
            credential.get_token("https://management.azure.com/.default")
        except ClientAuthenticationError:
            # Fall back to default credential
            print("CLI authentication failed, trying DefaultAzureCredential...")
            credential = DefaultAzureCredential()
            
        # Initialize clients
        resource_client = ResourceManagementClient(credential, os.environ.get("AZURE_SUBSCRIPTION_ID"))
        storage_client = StorageManagementClient(credential, os.environ.get("AZURE_SUBSCRIPTION_ID"))
        
        # Create resource group if it doesn't exist
        create_resource_group(resource_client, args.resource_group, args.location)
        
        # Create storage account
        storage_account = create_storage_account(
            storage_client, 
            args.resource_group,
            args.name,
            args.location
        )
        
        # Get connection string
        connection_string = get_storage_connection_string(
            storage_client,
            args.resource_group,
            args.name
        )
        
        # Create containers
        create_containers(connection_string)
        
        # Print connection string
        print("\n" + "="*80)
        print("STORAGE ACCOUNT CREATED SUCCESSFULLY")
        print("="*80)
        print("\nConnection String:")
        print(connection_string)
        print("\nTo use this connection string, add it to your environment variables:")
        print("\nLinux/Mac:")
        print(f'export AZURE_STORAGE_CONNECTION_STRING="{connection_string}"')
        print("\nWindows Command Prompt:")
        print(f'set AZURE_STORAGE_CONNECTION_STRING="{connection_string}"')
        print("\nWindows PowerShell:")
        print(f'$env:AZURE_STORAGE_CONNECTION_STRING="{connection_string}"')
        print("\nOr add it to your .env file or settings.py file")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()