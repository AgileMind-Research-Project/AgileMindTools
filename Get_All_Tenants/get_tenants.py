"""
AWS Lambda function to get tenant table list from MySQL database
"""

from database import read_from_mysql_with_params
import logging
import json
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_all_tables(exclude_system_tables=True):
    """
    Get all tables from the database, excluding system tables by default
    
    Args:
        exclude_system_tables (bool): If True, excludes 'roles' and 'password_reset_tokens' tables
    
    Returns:
        list: List of table names (tenant tables only if exclude_system_tables=True)
    """
    try:
        # Get the database schema from environment variable
        schema = os.getenv('DB_NAME')
        
        # System tables to exclude
        SYSTEM_TABLES = ['roles', 'password_reset_tokens']
        
        # Use parameterized query to get all tables
        query = "SHOW TABLES"
        result_df = read_from_mysql_with_params(query, {}, schema)
        
        # Extract table names from the DataFrame
        # The column name will be "Tables_in_<db_name>"
        column_name = result_df.columns[0]
        all_tables = result_df[column_name].tolist()
        
        # Filter out system tables if requested
        if exclude_system_tables:
            tables = [table for table in all_tables if table not in SYSTEM_TABLES]
            logger.info(f"Successfully retrieved {len(tables)} tenant tables (excluded {len(all_tables) - len(tables)} system tables)")
        else:
            tables = all_tables
            logger.info(f"Successfully retrieved {len(tables)} tables from database")
        
        return tables
        
    except Exception as e:
        logger.error(f"Error getting table list: {str(e)}")
        raise


def lambda_handler(event, context):
    """
    AWS Lambda handler function to get tenant table list
    
    Args:
        event (dict): Lambda event object
        context (object): Lambda context object
        
    Returns:
        dict: Response with statusCode and body containing array of table names
    """
    try:
        # Get list of all tables (excluding system tables by default)
        tables = get_all_tables(exclude_system_tables=True)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(tables, default=str)
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
    print("\n=== Getting all tenant table names ===")
    result = lambda_handler({}, None)
    print(json.dumps(json.loads(result['body']), indent=2))
