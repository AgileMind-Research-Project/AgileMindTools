"""
AWS Lambda function to get backlog items for projects 
whose next sprint starts in 4 days
"""

from database import read_from_mysql_with_params
from keys import get_credential
import logging
import json
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_projects_with_upcoming_sprint(tenant, days_before=4):
    """
    Retrieve projects whose next sprint starts in 'days_before' days.
    
    Args:
        tenant: Tenant name/database schema
        days_before: Number of days before next sprint start date (default: 4)
    
    Returns:
        List of project dictionaries with upcoming sprints
    """
    try:
        # Calculate target date (4 days from now)
        target_date = datetime.now().date() + timedelta(days=days_before)
        
        # Query to get projects where next_sprint_start_date matches target date
        project_query = """
        SELECT 
            project_id, 
            project_name, 
            `key`, 
            project_type,
            start_date,
            end_date,
            sprint_size,
            next_sprint_start_date,
            project_lead,
            architecture_type,
            stack_type,
            prioritize_task_count
        FROM projects 
        WHERE next_sprint_start_date = %(target_date)s AND project_id = '10406'
        
        """
        
        projects_df = read_from_mysql_with_params(
            project_query, 
            {'target_date': target_date}, 
            tenant
        )
        
        # Check if DataFrame is empty
        if projects_df.empty:
            logger.info(f"No projects found with next sprint starting on {target_date}")
            return []
        
        # Convert DataFrame to list of dictionaries
        projects = projects_df.to_dict('records')
        logger.info(f"Found {len(projects)} projects with sprint starting on {target_date}")
        return projects
        
    except Exception as e:
        logger.error(f"Error getting projects with upcoming sprint: {str(e)}")
        raise


def get_backlog_items_for_project(project_id, tenant):
    """
    Retrieve unassigned backlog items for a specific project.
    Only fetches items where sprint_id IS NULL (not yet assigned to any sprint).
    
    Args:
        project_id: Project ID
        tenant: Tenant name/database schema
    
    Returns:
        List of unassigned backlog item dictionaries
    """
    try:
        backlog_query = """
        SELECT 
            id,
            project_id,
            summary,
            description,
            issue_type,
            status,
            priority,
            assignee,
            tags,
            created_at,
            updated_at,
            severity,
            story_points,
            story_point_estimate
        FROM project_backlog 
        WHERE project_id = %(project_id)s
        AND status IN ('todo', 'in_progress')
        AND sprint_id IS NULL
        ORDER BY 
            CASE priority
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
                ELSE 4
            END,
            CASE issue_type
                WHEN 'bug' THEN 1
                WHEN 'feature' THEN 2
                WHEN 'story' THEN 3
                WHEN 'change' THEN 4
                ELSE 5
            END,
            created_at ASC
        """
        
        backlog_df = read_from_mysql_with_params(
            backlog_query, 
            {'project_id': project_id}, 
            tenant
        )
        
        # Check if DataFrame is empty
        if backlog_df.empty:
            logger.info(f"No backlog items found for project_id: {project_id}")
            return []
        
        # Convert DataFrame to list of dictionaries
        backlog_items = backlog_df.to_dict('records')
        logger.info(f"Found {len(backlog_items)} backlog items for project_id: {project_id}")
        return backlog_items
        
    except Exception as e:
        logger.error(f"Error getting backlog items for project {project_id}: {str(e)}")
        raise


def get_upcoming_sprint_backlog(tenant, days_before=4):
    """
    Main function to get all backlog items for projects with upcoming sprints.
    
    Args:
        tenant: Tenant name/database schema
        days_before: Number of days before next sprint start date (default: 4)
    
    Returns:
        Dictionary with projects and their backlog items
    """
    try:
        target_date = datetime.now().date() + timedelta(days=days_before)
        
        # Get projects with upcoming sprints
        projects = get_projects_with_upcoming_sprint(tenant, days_before)
        
        if not projects:
            return {
                'success': True,
                'message': f'No projects with sprint starting on {target_date}',
                'target_date': str(target_date),
                'days_before': days_before,
                'projects': []
            }
        
        # For each project, get backlog items
        result_data = []
        total_items = 0
        
        for project in projects:
            project_id = project['project_id']
            project_name = project['project_name']
            project_key = project['key']
            next_sprint_date = project.get('next_sprint_start_date')
            
            logger.info(f"Getting backlog for project: {project_name} ({project_key})")
            
            # Get backlog items for this project
            backlog_items = get_backlog_items_for_project(project_id, tenant)
            
            # Add project and its backlog to results
            result_data.append({
                'project_id': project_id,
                'project_name': project_name,
                'project_key': project_key,
                'next_sprint_start_date': str(next_sprint_date) if next_sprint_date else None,
                'sprint_size': project.get('sprint_size'),
                'project_lead': project.get('project_lead'),
                'architecture_type': project.get('architecture_type'),
                'stack_type': project.get('stack_type'),
                'prioritize_task_count': project.get('prioritize_task_count'),
                'backlog_items_count': len(backlog_items),
                'backlog_items': backlog_items
            })
            
            total_items += len(backlog_items)
        
        logger.info(f"Retrieved {total_items} total backlog items across {len(projects)} projects")
        
        return {
            'success': True,
            'target_date': str(target_date),
            'days_before': days_before,
            'projects_count': len(projects),
            'total_backlog_items': total_items,
            'projects': result_data
        }
        
    except Exception as e:
        logger.error(f"Error in get_upcoming_sprint_backlog: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def lambda_handler(event, context):
    """
    AWS Lambda handler function.
    
    Expected event structure:
    {
        "tenant": "tenant_name",
        "days_before": 4  // Optional, defaults to 4
    }
    
    Returns:
        API Gateway compatible response with backlog items for upcoming sprints
    """
    try:
        tenant = event.get('tenant')
        days_before = event.get('days_before', 4)
        
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
        
        # Validate days_before parameter
        try:
            days_before = int(days_before)
            if days_before < 0:
                raise ValueError("days_before must be non-negative")
        except (ValueError, TypeError) as e:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'error': f'Invalid days_before parameter: {str(e)}'
                })
            }
        
        # Get upcoming sprint backlog items
        result = get_upcoming_sprint_backlog(tenant, days_before)
        
        return {
            'statusCode': 200 if result['success'] else 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result, default=str)
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
    # Disable logging for cleaner output
    logging.basicConfig(level=logging.ERROR)
    
    # Test event
    test_event = {
        "tenant": "sliit",  # Change to your tenant name
        "days_before": 4
    }
    
    result = lambda_handler(test_event, None)
    
    # Extract and print only the projects list
    body = json.loads(result['body'])
    
    if body.get('success'):
        projects = body.get('projects', [])
        print(json.dumps(projects, indent=2, default=str))
    else:
        print(json.dumps({"error": body.get('error')}, indent=2))
