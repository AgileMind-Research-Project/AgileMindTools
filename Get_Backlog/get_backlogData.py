"""
AWS Lambda function to get Jira backlog data and store in MySQL database
"""

from database import read_from_mysql_with_params, execute_query
from keys import get_credential
from sqlalchemy import text
import logging
import json
from atlassian import Jira
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configuration: Jira Custom Field IDs
# Change these to match your Jira instance's custom field IDs
# To find your custom field IDs:
# 1. Go to Jira Admin > Issues > Custom Fields
# 2. Or use the API: /rest/api/3/field
# 3. Or inspect element on a Jira issue page
SEVERITY_FIELD_ID = 'customfield_10165'
STORY_POINTS_FIELD_ID = 'customfield_10035'  # Story Points field (Company-managed)
STORY_POINT_ESTIMATE_FIELD_ID = 'customfield_10016'  # Story Point Estimate field (Team-managed)
START_DATE_FIELD_ID = 'customfield_10015'    # Start Date field


def get_all_project(tenant):
    """
    Retrieve all projects from the database for a given tenant.
    
    Args:
        tenant: Tenant name
    
    Returns:
        List of project dictionaries with project_id, project_name, and key
    """
    try:
        project_query = "SELECT project_id, project_name, `key` FROM projects where project_id = 10237"
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


def get_jira_credentials(tenant):
    """
    Get Jira API credentials for a tenant.
    Fetches jira_url and email from jira_integrations table,
    and api_token from AWS Secrets Manager.
    
    Args:
        tenant: Tenant name/database schema
    
    Returns:
        Dictionary with jira_url, email, and api_token
    """
    try:
        # Get Jira URL and email from jira_integrations table
        jira_query = "SELECT jira_url, email FROM jira_integrations LIMIT 1"
        jira_df = read_from_mysql_with_params(jira_query, {}, tenant)
        
        if jira_df.empty:
            logger.error(f"No Jira integration found in database for tenant: {tenant}")
            return None
        
        # Extract first row
        jira_record = jira_df.iloc[0]
        jira_url = jira_record['jira_url']
        email = jira_record['email']
        
        # Get API token from AWS Secrets Manager
        credentials = get_credential(tenant)
        
        if not credentials:
            logger.error(f"No Jira API token found in AWS Secrets Manager for tenant: {tenant}")
            return None
        
        # Extract the API token
        cred = credentials[0]['secret_value']
        
        # Parse the credential based on its format
        if isinstance(cred, dict):
            api_token = cred.get('api_token')
        elif isinstance(cred, str):
            # If it's just a string, assume it's the token itself
            api_token = cred
        else:
            logger.error(f"Unexpected credential format for tenant: {tenant}")
            return None
        
        if not api_token:
            logger.error(f"API token is empty for tenant: {tenant}")
            return None
        
        logger.info(f"Successfully retrieved Jira credentials for tenant: {tenant}")
        return {
            'jira_url': jira_url,
            'email': email,
            'api_token': api_token
        }
            
    except Exception as e:
        logger.error(f"Error getting Jira credentials: {str(e)}")
        raise


def fetch_jira_backlog(jira_url, email, api_token, project_key):
    """
    Fetch backlog items from Jira for a specific project using Atlassian API.
    
    Args:
        jira_url: Jira instance URL
        email: Jira user email
        api_token: Jira API token
        project_key: Project key (e.g., 'AMNT')
    
    Returns:
        List of Jira issues
    """
    try:
        # Connect to Jira using atlassian-python-api (supports latest Jira Cloud API)
        jira_client = Jira(
            url=jira_url,
            username=email,
            password=api_token,
            cloud=True
        )
        
        # JQL to get all issues for the project
        jql = f'project = "{project_key}" ORDER BY created DESC'
        
        logger.info(f"Fetching issues for project {project_key} with JQL: {jql}")
        
        # Use jql() method to search issues - returns all results with pagination
        all_issues = jira_client.jql(jql, limit=1000)
        
        issues_list = all_issues.get('issues', [])
        logger.info(f"Fetched {len(issues_list)} backlog items for project {project_key}")
        return issues_list
        
    except Exception as e:
        logger.error(f"Error fetching Jira backlog: {str(e)}")
        raise


def transform_jira_issue(issue, project_id):
    """
    Transform a Jira issue object (from atlassian-python-api) to match the project_backlog table schema.
    
    Args:
        issue: Jira issue dictionary from atlassian-python-api
        project_id: Internal project ID from database
    
    Returns:
        Dictionary matching the project_backlog table structure with id, tags, etc.
    """
    try:
        # Extract Jira issue key (e.g., "NPTM-1") as the id
        issue_key = issue.get('key', '')
        
        # Access fields from Jira issue dictionary (from atlassian-python-api)
        fields = issue.get('fields', {})
        
        # Extract issue type and map to our schema
        issue_type_obj = fields.get('issuetype', {})
        issue_type_name = issue_type_obj.get('name', '').lower()
        
        # Map Jira issue types to our types: story, feature, change, bug
        type_mapping = {
            'story': 'story',
            'user story': 'story',
            'feature': 'feature',
            'new feature': 'feature',
            'epic': 'feature',
            'bug': 'bug',
            'defect': 'bug',
            'change': 'change',
            'improvement': 'change',
            'task': 'change'
        }
        
        issue_type = type_mapping.get(issue_type_name, 'story')
        
        # Extract status and map to our schema
        status_obj = fields.get('status', {})
        status_name = status_obj.get('name', '').lower()
        
        # Map Jira statuses to our statuses: todo, in_progress, done
        status_mapping = {
            'backlog': 'todo',
            'to do': 'todo',
            'todo': 'todo',
            'open': 'todo',
            'in progress': 'in_progress',
            'in-progress': 'in_progress',
            'in development': 'in_progress',
            'done': 'done',
            'closed': 'done',
            'resolved': 'done',
            'complete': 'done'
        }
        
        status = status_mapping.get(status_name, 'todo')
        
        # Extract priority
        priority_obj = fields.get('priority', {})
        priority_name = priority_obj.get('name', '').lower() if priority_obj else None
        
        # Map Jira priorities to our priorities: high, medium, low
        if priority_name:
            priority_mapping = {
                'highest': 'high',
                'high': 'high',
                'medium': 'medium',
                'low': 'low',
                'lowest': 'low',
                'critical': 'high',
                'major': 'high',
                'minor': 'low',
                'trivial': 'low'
            }
            priority = priority_mapping.get(priority_name, 'medium')
        else:
            priority = None
        
        # Extract assignee - use email instead of display name
        assignee_obj = fields.get('assignee', {})
        if assignee_obj:
            logger.info(f"Assignee object for {issue_key}: {assignee_obj}")
            assignee = assignee_obj.get('emailAddress')
            if assignee:
                logger.info(f"Found assignee email '{assignee}' for issue {issue_key}")
            else:
                logger.warning(f"No emailAddress found in assignee object for issue {issue_key}")
        else:
            assignee = None
            logger.info(f"No assignee set for issue {issue_key}")
        
        # Extract description
        description = fields.get('description', '')
        
        # Extract labels (tags) as a list for JSON storage
        labels = fields.get('labels', [])
        
        # Extract Severity custom field (uses SEVERITY_FIELD_ID constant)
        # Severity is stored as a list/object in custom fields
        severity = None
        
        # Try to extract severity from the custom field
        if SEVERITY_FIELD_ID in fields and fields[SEVERITY_FIELD_ID]:
            severity_value = fields[SEVERITY_FIELD_ID]
            
            # Handle if it's a list of objects
            if isinstance(severity_value, list) and len(severity_value) > 0:
                item = severity_value[0]
                if isinstance(item, dict):
                    severity = item.get('value') or item.get('name')
                else:
                    severity = str(item)
            # Handle if it's an object with value/name attribute
            elif isinstance(severity_value, dict):
                severity = severity_value.get('value') or severity_value.get('name')
            # Handle if it's a plain string
            elif isinstance(severity_value, str):
                severity = severity_value
            else:
                severity = str(severity_value)
            
            # Normalize to lowercase if found
            if severity:
                severity = str(severity).lower()
                logger.info(f"Found severity '{severity}' in field '{SEVERITY_FIELD_ID}' for issue {issue_key}")
        
        # Fallback: check if there's a 'severity' field directly (some Jira instances)
        if not severity and 'severity' in fields and fields['severity']:
            severity_obj = fields['severity']
            if isinstance(severity_obj, dict):
                severity = severity_obj.get('value', severity_obj.get('name', ''))
            elif isinstance(severity_obj, str):
                severity = severity_obj
            
            if severity:
                severity = str(severity).lower()
        
        # Extract Story Points custom field
        story_points = None
        
        # Try to extract story points from the custom field
        if STORY_POINTS_FIELD_ID in fields and fields[STORY_POINTS_FIELD_ID] is not None:
            story_points_value = fields[STORY_POINTS_FIELD_ID]
            
            # Handle different data types for story points
            try:
                # Story points can be int, float, or string representing a number
                if isinstance(story_points_value, (int, float)):
                    story_points = int(story_points_value)
                elif isinstance(story_points_value, str):
                    # Try to convert string to int
                    story_points = int(float(story_points_value))
                else:
                    logger.warning(f"Unexpected story points format for issue {issue_key}: {type(story_points_value)}")
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not parse story points for issue {issue_key}: {story_points_value} - {str(e)}")
                story_points = None
            
            if story_points is not None:
                logger.info(f"Found story points '{story_points}' in field '{STORY_POINTS_FIELD_ID}' for issue {issue_key}")
        
        # Extract Story Point Estimate custom field (Team-managed project)
        story_point_estimate = None
        
        # Try to extract story point estimate from the custom field
        if STORY_POINT_ESTIMATE_FIELD_ID in fields and fields[STORY_POINT_ESTIMATE_FIELD_ID] is not None:
            spe_value = fields[STORY_POINT_ESTIMATE_FIELD_ID]
            
            # Handle different data types for story point estimate
            try:
                # Value can be int, float, or string representing a number
                if isinstance(spe_value, (int, float)):
                    story_point_estimate = int(spe_value)
                elif isinstance(spe_value, str):
                    # Try to convert string to int
                    story_point_estimate = int(float(spe_value))
                else:
                    logger.warning(f"Unexpected story point estimate format for issue {issue_key}: {type(spe_value)}")
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not parse story point estimate for issue {issue_key}: {spe_value} - {str(e)}")
                story_point_estimate = None
            
            if story_point_estimate is not None:
                logger.info(f"Found story point estimate '{story_point_estimate}' in field '{STORY_POINT_ESTIMATE_FIELD_ID}' for issue {issue_key}")
        
        # Extract dates
        created_at = fields.get('created')
        updated_at = fields.get('updated')
        
        # Parse dates (Jira library returns datetime strings)
        if created_at:
            # Handle different datetime formats
            try:
                created_at = datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%S.%f%z').strftime('%Y-%m-%d %H:%M:%S')
            except:
                try:
                    created_at = datetime.strptime(created_at[:19], '%Y-%m-%dT%H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
                except:
                    logger.warning(f"Could not parse created_at date: {created_at}")
                    created_at = None
        
        if updated_at:
            try:
                updated_at = datetime.strptime(updated_at, '%Y-%m-%dT%H:%M:%S.%f%z').strftime('%Y-%m-%d %H:%M:%S')
            except:
                try:
                    updated_at = datetime.strptime(updated_at[:19], '%Y-%m-%dT%H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
                except:
                    logger.warning(f"Could not parse updated_at date: {updated_at}")
                    updated_at = None
        
        # Extract Start Date from custom field
        jira_start_date = fields.get(START_DATE_FIELD_ID)
        start_date = None
        end_date = None
        
        # Use Jira start date if available
        if jira_start_date:
            try:
                # Jira start date is in format 'YYYY-MM-DD'
                start_date = datetime.strptime(jira_start_date, '%Y-%m-%d').strftime('%Y-%m-%d')
                logger.info(f"Found start date '{start_date}' in field '{START_DATE_FIELD_ID}' for issue {issue_key}")
            except Exception as e:
                logger.warning(f"Could not parse start date: {jira_start_date} - {str(e)}")
                # Fallback to created date
                if created_at:
                    try:
                        start_date = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
                    except:
                        start_date = datetime.now().strftime('%Y-%m-%d')
                else:
                    start_date = datetime.now().strftime('%Y-%m-%d')
        else:
            # Fallback to created date if no custom start date
            if created_at:
                try:
                    start_date = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
                except:
                    try:
                        if 'T' in str(created_at):
                            start_date = datetime.strptime(str(created_at)[:10], '%Y-%m-%d').strftime('%Y-%m-%d')
                        else:
                            start_date = datetime.now().strftime('%Y-%m-%d')
                    except:
                        start_date = datetime.now().strftime('%Y-%m-%d')
            else:
                start_date = datetime.now().strftime('%Y-%m-%d')
        
        # Extract due date for end_date
        due_date = fields.get('duedate')
        
        # Use due date as end_date if available, otherwise add 14 days to start_date
        if due_date:
            try:
                end_date = datetime.strptime(due_date, '%Y-%m-%d').strftime('%Y-%m-%d')
            except:
                logger.warning(f"Could not parse due date: {due_date}")
                # Fallback: add 14 days to start date
                end_date = (datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=14)).strftime('%Y-%m-%d')
        else:
            # Default: add 14 days to start date (typical sprint length)
            end_date = (datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=14)).strftime('%Y-%m-%d')
        
        # Extract estimated hours from time tracking
        # Jira stores time in seconds in timeoriginalestimate
        estimated_hours = 0
        time_estimate_seconds = fields.get('timeoriginalestimate')
        
        if time_estimate_seconds:
            try:
                # Convert seconds to hours (round to nearest integer)
                estimated_hours = int(round(time_estimate_seconds / 3600))
                logger.info(f"Found estimated hours '{estimated_hours}' (from {time_estimate_seconds} seconds) for issue {issue_key}")
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not parse time estimate for issue {issue_key}: {time_estimate_seconds} - {str(e)}")
                estimated_hours = 0
        
        return {
            'id': issue_key,
            'project_id': project_id,
            'summary': fields.get('summary', ''),
            'description': description,
            'issue_type': issue_type,
            'status': status,
            'priority': priority,
            'assignee': assignee,
            'tags': json.dumps(labels) if labels else None,  # Store as JSON string
            'created_at': created_at,
            'updated_at': updated_at,
            'severity': severity,  # Add severity field
            'story_points': story_points,  # Add story points field (Company-managed)
            'story_point_estimate': story_point_estimate,  # Add story point estimate (Team-managed)
            'estimated_hours': estimated_hours,  # Add estimated hours
            'start_date': start_date,  # Add start_date
            'end_date': end_date  # Add end_date
        }
        
    except Exception as e:
        logger.error(f"Error transforming Jira issue: {str(e)}")
        raise


def extract_text_from_adf(adf_content):
    """
    Extract plain text from Atlassian Document Format (ADF).
    
    Args:
        adf_content: ADF content dictionary
    
    Returns:
        Plain text string
    """
    try:
        if not isinstance(adf_content, dict):
            return str(adf_content) if adf_content else None
        
        def extract_text(node):
            if isinstance(node, str):
                return node
            
            if not isinstance(node, dict):
                return ''
            
            text_parts = []
            
            # Handle text node
            if node.get('type') == 'text':
                return node.get('text', '')
            
            # Handle nodes with content
            if 'content' in node:
                for child in node['content']:
                    text_parts.append(extract_text(child))
            
            return ' '.join(text_parts)
        
        extracted = extract_text(adf_content)
        return extracted.strip() if extracted else None
        
    except Exception as e:
        logger.warning(f"Error extracting text from ADF: {str(e)}")
        return str(adf_content) if adf_content else None


def delete_removed_items(project_id, jira_issue_keys, tenant):
    """
    Delete backlog items from database that no longer exist in Jira.
    
    Args:
        project_id: Project ID to check
        jira_issue_keys: List of issue keys currently in Jira
        tenant: Tenant name
    
    Returns:
        Number of items deleted
    """
    try:
        # Get all existing issue IDs for this project from database
        select_query = "SELECT id FROM project_backlog WHERE project_id = %(project_id)s"
        existing_df = read_from_mysql_with_params(select_query, {'project_id': project_id}, tenant)
        
        if existing_df.empty:
            logger.info("No existing backlog items in database")
            return 0
        
        # Get list of existing IDs
        existing_ids = existing_df['id'].tolist()
        
        # Find IDs that exist in database but not in Jira (these were deleted)
        jira_keys_set = set(jira_issue_keys)
        ids_to_delete = [item_id for item_id in existing_ids if item_id not in jira_keys_set]
        
        if not ids_to_delete:
            logger.info("No items to delete")
            return 0
        
        # Delete items that no longer exist in Jira
        delete_count = 0
        delete_query = "DELETE FROM project_backlog WHERE id = :id"
        
        for item_id in ids_to_delete:
            try:
                result = execute_query(delete_query, {'id': item_id}, tenant)
                if result:
                    delete_count += 1
                    logger.info(f"Deleted backlog item: {item_id}")
            except Exception as e:
                logger.error(f"Error deleting item {item_id}: {str(e)}")
                continue
        
        logger.info(f"Deleted {delete_count} backlog items that were removed from Jira")
        return delete_count
        
    except Exception as e:
        logger.error(f"Error in delete_removed_items: {str(e)}")
        return 0


def insert_backlog_items(backlog_items, tenant):
    """
    Insert or update backlog items in the database.
    
    Args:
        backlog_items: List of backlog item dictionaries
        tenant: Tenant name
    
    Returns:
        Number of items inserted/updated
    """
    try:
        if not backlog_items:
            logger.info("No backlog items to insert")
            return 0
        
        # Use INSERT ... ON DUPLICATE KEY UPDATE to handle existing records
        # The id (Jira issue key) is the primary key, so duplicates will be updated
        insert_query = """
        INSERT INTO project_backlog 
        (id, project_id, summary, description, issue_type, status, priority, assignee, tags, created_at, updated_at, severity, story_points, story_point_estimate, estimated_hours, start_date, end_date)
        VALUES 
        (:id, :project_id, :summary, :description, :issue_type, :status, :priority, :assignee, :tags, :created_at, :updated_at, :severity, :story_points, :story_point_estimate, :estimated_hours, :start_date, :end_date)
        ON DUPLICATE KEY UPDATE
            summary = VALUES(summary),
            description = VALUES(description),
            issue_type = VALUES(issue_type),
            status = VALUES(status),
            priority = VALUES(priority),
            assignee = VALUES(assignee),
            tags = VALUES(tags),
            updated_at = VALUES(updated_at),
            severity = VALUES(severity),
            story_points = VALUES(story_points),
            story_point_estimate = VALUES(story_point_estimate),
            estimated_hours = VALUES(estimated_hours),
            start_date = VALUES(start_date),
            end_date = VALUES(end_date)
        """
        
        success_count = 0
        for item in backlog_items:
            try:
                result = execute_query(insert_query, item, tenant)
                if result:
                    success_count += 1
            except Exception as e:
                logger.error(f"Error inserting backlog item: {str(e)}")
                continue
        
        logger.info(f"Successfully inserted/updated {success_count} backlog items")
        return success_count
        
    except Exception as e:
        logger.error(f"Error in insert_backlog_items: {str(e)}")
        raise


def sync_jira_backlog(tenant):
    """
    Main function to sync Jira backlog data to the database.
    
    Args:
        tenant: Tenant name
    
    Returns:
        Dictionary with sync results
    """
    try:
        # Get Jira credentials
        credentials = get_jira_credentials(tenant)
        if not credentials:
            return {
                'success': False,
                'error': 'Failed to get Jira credentials'
            }
        
        jira_url = credentials['jira_url']
        email = credentials['email']
        api_token = credentials['api_token']
        
        # Get all projects
        projects = get_all_project(tenant)
        if not projects:
            logger.info("No projects found")
            return {
                'success': True,
                'message': 'No projects found',
                'projects_synced': 0,
                'items_synced': 0
            }
        
        total_items = 0
        total_deleted = 0
        projects_synced = 0
        
        # For each project, fetch and store backlog items
        for project in projects:
            project_id = project['project_id']
            project_key = project['key']
            project_name = project['project_name']
            
            logger.info(f"Syncing backlog for project: {project_name} ({project_key})")
            
            try:
                # Fetch Jira backlog items
                jira_issues = fetch_jira_backlog(jira_url, email, api_token, project_key)
                
                # Extract issue keys for deletion check
                jira_issue_keys = [issue.get('key') for issue in jira_issues if issue.get('key')]
                
                # Transform issues to match our schema
                backlog_items = [transform_jira_issue(issue, project_id) for issue in jira_issues]
                
                # Insert/Update into database
                items_count = insert_backlog_items(backlog_items, tenant)
                
                # Delete items that were removed from Jira
                deleted_count = delete_removed_items(project_id, jira_issue_keys, tenant)
                
                total_items += items_count
                total_deleted += deleted_count
                projects_synced += 1
                
                logger.info(f"Synced {items_count} items for project {project_name}")
                if deleted_count > 0:
                    logger.info(f"Deleted {deleted_count} items that were removed from Jira")
                
            except Exception as e:
                logger.error(f"Error syncing project {project_name}: {str(e)}")
                continue
        
        return {
            'success': True,
            'projects_synced': projects_synced,
            'items_synced': total_items,
            'items_deleted': total_deleted
        }
        
    except Exception as e:
        logger.error(f"Error in sync_jira_backlog: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }





def lambda_handler(event, context):
    """
    Lambda handler supporting multiple actions:
    - 'get_projects': Get list of all projects
    - 'sync_backlog': Sync Jira backlog data to database
    """
    try:
        tenant = event.get('tenant')
        action = event.get('action', 'get_projects')
        
        if not tenant:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'error': 'tenant parameter is required'
                })
            }
        
        if action == 'sync_backlog':
            # Sync Jira backlog to database
            result = sync_jira_backlog(tenant)
            return {
                'statusCode': 200 if result['success'] else 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(result, default=str)
            }
        else:
            # Default: Get all projects
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
    # Test 1: Get all projects
    print("\n=== Getting all projects ===")
    result = lambda_handler({"tenant": "sliit", "action": "get_projects"}, None)
    print(json.dumps(json.loads(result['body']), indent=2))
    
    # Test 2: Sync Jira backlog
    print("\n\n=== Syncing Jira backlog ===")
    result = lambda_handler({"tenant": "sliit", "action": "sync_backlog"}, None)
    print(json.dumps(json.loads(result['body']), indent=2))
