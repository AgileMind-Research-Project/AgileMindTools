import boto3
import botocore 
import botocore.session 
import json
from aws_secretsmanager_caching import SecretCache, SecretCacheConfig 

def get_credential(tenant_name):
    """
    Get Jira API token credentials for a specific tenant from AWS Secrets Manager.
    
    Args:
        tenant_name: The tenant name to filter (e.g., 'sliit')
    
    Returns:
        List of dictionaries with 'secret_name' and 'secret_value' for all matching Jira API token secrets,
        or empty list if not found
    """
    client = boto3.client("secretsmanager")
    
    # Build the search pattern for the tenant
    search_pattern = f"tenant_{tenant_name}_"
    
    # Store all matching secrets
    matching_secrets = []
    
    paginator = client.get_paginator("list_secrets")

    for page in paginator.paginate():
        for item in page.get("SecretList", []):
            name = item["Name"]
            
            # Check if this secret matches the tenant pattern AND contains jira_api_token
            if search_pattern in name and "jira_api_token" in name:
                # Get the secret's decrypted value
                value_resp = client.get_secret_value(SecretId=name)

                if "SecretString" in value_resp:
                    value_raw = value_resp["SecretString"]
                else:
                    value_raw = value_resp["SecretBinary"].decode("utf-8")

                # Try convert value to JSON (if it's JSON)
                try:
                    value = json.loads(value_raw)
                except:
                    value = value_raw

                # Add this secret to the list
                matching_secrets.append({
                    "secret_name": name,
                    "secret_value": value
                })
    
    return matching_secrets


# Example usage: Get credentials for 'sliit' tenant
# tenant = "sliit"
# data = get_credential(tenant)
# print(data)
# if data:
#     print(f"Found {len(data)} secret(s) for tenant '{tenant}':")
#     for idx, secret in enumerate(data, 1):
#         print(f"\nSecret {idx}:")
#         print(f"  Name: {secret['secret_name']}")
#         print(f"  Value: {secret['secret_value']}")
# else:
#     print(f"No secrets found for tenant '{tenant}'")


