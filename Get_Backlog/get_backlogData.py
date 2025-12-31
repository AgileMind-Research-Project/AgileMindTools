"""
AWS Lambda function to get tenant table list from MySQL database
"""

from database import read_from_mysql_with_params
from sqlalchemy import text
import logging
import json

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_all_project(tenant):
    try:
        project_query = "SELECT project_id, project_name, `key` FROM projects"
        projects_df = read_from_mysql_with_params(project_query, {}, tenant)
        
        # Check if DataFrame is empty before converting
        if projects_df.empty:
            return []
        
        # Convert DataFrame to list of dictionaries
        projects = projects_df.to_dict('records')
        return projects
    except Exception as e:
        logger.error(f"Error getting project list: {str(e)}")
        raise





def lambda_handler(event, context):
    try:
        tenant = event['tenant']
        projects = get_all_project(tenant)
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(projects, default=str)
        }
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }


# For local testing
if __name__ == "__main__":
    print("\n=== Getting all projects ===")
    result = lambda_handler({"tenant": "sliit"}, None)
    print(json.dumps(json.loads(result['body']), indent=2))
