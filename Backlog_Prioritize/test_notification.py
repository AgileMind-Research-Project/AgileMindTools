"""
Test script to debug notification creation
This script will help identify why notifications are not being created
"""

import os
import sys
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import read_from_mysql_with_params
from prioritize_upcoming_sprints import create_notification_for_project_managers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_notification():
    """Test notification creation for a specific project"""
    
    # CONFIGURE THESE VALUES
    project_id = 10270  # Replace with your actual project ID
    tenant = "sliit"     # Replace with your tenant name
    items_count = 15     # Number of prioritized items
    
    logger.info("="*80)
    logger.info("NOTIFICATION DEBUG TEST")
    logger.info("="*80)
    logger.info(f"Project ID: {project_id}")
    logger.info(f"Tenant: {tenant}")
    logger.info(f"Items Count: {items_count}")
    logger.info("")
    
    # Check if project exists and has project_manager
    logger.info("Step 1: Checking project in database...")
    project_query = """
    SELECT project_id, project_name, project_manager
    FROM projects
    WHERE project_id = %(project_id)s
    """
    
    project_df = read_from_mysql_with_params(
        project_query,
        {'project_id': project_id},
        tenant
    )
    
    if project_df.empty:
        logger.error(f"❌ Project {project_id} not found!")
        return
    
    logger.info(f"✅ Project found: {project_df.iloc[0]['project_name']}")
    logger.info(f"   Project manager field: {project_df.iloc[0].get('project_manager')}")
    logger.info("")
    
    # Check API URL
    logger.info("Step 2: Checking API URL configuration...")
    api_url = os.getenv('API_URL', 'http://localhost:8000')
    logger.info(f"   API URL: {api_url}")
    logger.info("")
    
    # Test API connectivity
    logger.info("Step 3: Testing API connectivity...")
    try:
        import requests
        health_check = requests.get(f"{api_url}/health", timeout=5)
        logger.info(f"   ✅ API is reachable: {health_check.status_code}")
    except Exception as e:
        logger.error(f"   ❌ Cannot reach API: {str(e)}")
        logger.error(f"   Please ensure the API server is running at {api_url}")
        return
    
    logger.info("")
    
    # Try to create notification
    logger.info("Step 4: Creating notification...")
    logger.info("="*80)
    
    try:
        create_notification_for_project_managers(project_id, items_count, tenant)
        logger.info("")
        logger.info("="*80)
        logger.info("✅ NOTIFICATION TEST COMPLETED SUCCESSFULLY!")
        logger.info("="*80)
    except Exception as e:
        logger.error("")
        logger.error("="*80)
        logger.error(f"❌ NOTIFICATION TEST FAILED!")
        logger.error(f"Error: {str(e)}")
        logger.error("="*80)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("\n")
    print("🔔 NOTIFICATION DEBUGGING TOOL")
    print("="*80)
    print("This script will help debug why notifications are not being created")
    print("="*80)
    print("\n")
    
    # You can set API_URL environment variable before running
    # Example: set API_URL=http://localhost:8000 (Windows)
    # Example: export API_URL=http://localhost:8000 (Linux/Mac)
    
    test_notification()
