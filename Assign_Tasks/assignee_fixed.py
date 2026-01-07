from database import read_from_mysql_with_params
import logging
import json

# Lambda-style function to get developers from the database
get_developers = lambda tenant, project: fetch_developers_from_db(tenant, project)

def fetch_developers_from_db(tenant, project):
    """
    Fetch user details from the sliit table and format them as developers master list.
    
    Args:
        tenant (str): The tenant table name (e.g., 'sliit')
        project (str): The project_id to filter users by
    
    Returns:
        list: List of developer dictionaries with email, stack, technologies, and experience_years
    """
    tenant_db = "agilemind_db"
    try:
        # SQL query to fetch user details from sliit table
        # Using JSON_CONTAINS to search for project_id (as integer) in the projects JSON array
        sql_query = f"""
            SELECT 
                email,
                first_name,
                last_name,
                role,
                status,
                user_data
            FROM {tenant}
            WHERE status = 'ACTIVE'
                AND JSON_CONTAINS(projects, '{project}')
        """
        
        # Fetch data from database
        df = read_from_mysql_with_params(sql_query, {}, tenant_db)
        
        # Check if data is empty
        if df.empty:
            logging.warning(f"No active users found in tenant: {tenant_db}")
            return []
        
        # Convert dataframe to list of dictionaries
        developers_master = []
        
        for _, row in df.iterrows():
            # Parse user_data JSON if it exists
            user_data = {}
            if row['user_data'] and row['user_data'] != 'null':
                try:
                    user_data = json.loads(row['user_data']) if isinstance(row['user_data'], str) else row['user_data']
                except json.JSONDecodeError:
                    logging.warning(f"Could not parse user_data for {row['email']}")
                    user_data = {}
            
            # Create developer entry
            developer = {
                "email": row['email'],
                "stack": user_data.get('stack', ["backend"]),  # Default to backend if not specified
                "technologies": user_data.get('technologies', []),  # Empty list if not specified
                "experience_years": user_data.get('experience_years', 0)  # Default to 0 if not specified
            }
            
            developers_master.append(developer)
        
        logging.info(f"Successfully fetched {len(developers_master)} developers from tenant: {tenant}")
        return developers_master
        
    except Exception as e:
        logging.error(f"Error fetching developers from database: {str(e)}")
        return []


def get_developer_by_email(tenant, project, email):
    """
    Get a specific developer by email.
    
    Args:
        tenant (str): The tenant table name
        project (str): The project_id to filter users by
        email (str): Developer's email address
    
    Returns:
        dict: Developer information or None if not found
    """
    developers = get_developers(tenant, project)
    for developer in developers:
        if developer['email'] == email:
            return developer
    return None


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
        logging.error(f"Error getting project list: {str(e)}")
        raise


def get_unassigned_parent_tasks(project_id, tenant_db):
    """
    Get parent backlog items that don't have a sprint assigned (sprint_id IS NULL).
    
    Args:
        project_id: Project ID to filter by
        tenant_db: Database name
    
    Returns:
        List of unassigned parent task IDs
    """
    try:
        query = """
            SELECT DISTINCT pbp.backlog_id
            FROM project_backlog_priority pbp
            WHERE pbp.project_id = %(project_id)s
                AND pbp.sprint_id IS NULL
            ORDER BY pbp.rank
        """
        
        params = {'project_id': project_id}
        df = read_from_mysql_with_params(query, params, tenant_db)
        
        if df.empty:
            logging.info(f"No unassigned parent tasks found for project {project_id}")
            return []
        
        # Return list of backlog IDs
        return df['backlog_id'].tolist()
    
    except Exception as e:
        logging.error(f"Error getting unassigned parent tasks: {str(e)}")
        return []


def get_subtasks_by_parent_ids(parent_ids, tenant_db):
    """
    Get all subtasks where parent_task_id matches the given parent IDs.
    
    Args:
        parent_ids: List of parent task IDs
        tenant_db: Database name
    
    Returns:
        List of subtask dictionaries
    """
    try:
        if not parent_ids:
            return []
        
        # Create placeholders for the IN clause
        placeholders = ','.join(['%s'] * len(parent_ids))
        
        query = f"""
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
                estimated_hours,
                story_points,
                parent_task_id,
                start_date,
                end_date
            FROM project_backlog
            WHERE parent_task_id IN ({placeholders})
                AND status = 'todo'
            ORDER BY priority DESC, story_points DESC
        """
        
        df = read_from_mysql_with_params(query, tuple(parent_ids), tenant_db)
        
        if df.empty:
            logging.info(f"No subtasks found for parent IDs: {parent_ids}")
            return []
        
        # Convert to list of dictionaries
        subtasks = df.to_dict('records')
        
        # Parse tags JSON if exists
        for task in subtasks:
            if task.get('tags') and isinstance(task['tags'], str):
                try:
                    task['tags'] = json.loads(task['tags'])
                except:
                    task['tags'] = []
        
        return subtasks
    
    except Exception as e:
        logging.error(f"Error getting subtasks: {str(e)}")
        return []


def get_developer_work_history(project_id, tenant_table, tenant_db):
    """
    Analyze developer work history for a project.
    
    Args:
        project_id: Project ID
        tenant_table: Tenant table name (e.g., 'sliit')
        tenant_db: Database name
    
    Returns:
        Dictionary mapping developer emails to their work history stats
    """
    try:
        query = """
            SELECT 
                assignee,
                issue_type,
                COUNT(*) as task_count,
                SUM(story_points) as total_points,
                AVG(estimated_hours) as avg_hours
            FROM project_backlog
            WHERE project_id = %(project_id)s
                AND assignee IS NOT NULL
                AND assignee != ''
                AND status IN ('done', 'in_progress')
            GROUP BY assignee, issue_type
        """
        
        params = {'project_id': project_id}
        df = read_from_mysql_with_params(query, params, tenant_db)
        
        work_history = {}
        for _, row in df.iterrows():
            email = row['assignee']
            if email not in work_history:
                work_history[email] = {
                    'total_tasks': 0,
                    'total_points': 0,
                    'issue_types': {}
                }
            
            work_history[email]['total_tasks'] += row['task_count']
            work_history[email]['total_points'] += row['total_points'] or 0
            work_history[email]['issue_types'][row['issue_type']] = row['task_count']
        
        return work_history
    
    except Exception as e:
        logging.error(f"Error getting developer work history: {str(e)}")
        return {}


def assign_tasks_to_developers(project_id, tenant_table, tenant_db):
    """
    Main function to assign subtasks to developers based on their skills and work history.
    
    Args:
        project_id: Project ID
        tenant_table: Tenant table name (e.g., 'sliit')
        tenant_db: Database name
    
    Returns:
        List of assignment dictionaries with task_id and assigned developer
    """
    try:
        logging.info(f"Starting task assignment for project {project_id}")
        
        # Step 1: Get unassigned parent tasks
        parent_task_ids = get_unassigned_parent_tasks(project_id, tenant_db)
        if not parent_task_ids:
            logging.warning(f"No unassigned parent tasks for project {project_id}")
            return []
        
        logging.info(f"Found {len(parent_task_ids)} unassigned parent tasks")
        
        # Step 2: Get subtasks
        subtasks = get_subtasks_by_parent_ids(parent_task_ids, tenant_db)
        if not subtasks:
            logging.warning(f"No subtasks found for parent tasks")
            return []
        
        logging.info(f"Found {len(subtasks)} subtasks to assign")
        
        # Step 3: Get developers for this project
        developers = get_developers(tenant_table, str(project_id))
        if not developers:
            logging.warning(f"No developers found for project {project_id}")
            return []
        
        logging.info(f"Found {len(developers)} developers")
        
        # Step 4: Get work history
        work_history = get_developer_work_history(project_id, tenant_table, tenant_db)
        
        # Step 5: Assign tasks based on matching logic
        assignments = []
        developer_workload = {dev['email']: 0 for dev in developers}
        
        for task in subtasks:
            best_match = None
            best_score = -1
            
            # Extract task requirements from tags
            task_tags = task.get('tags', [])
            task_type = task.get('issue_type', '').lower()
            
            for developer in developers:
                dev_email = developer['email']
                dev_stack = developer.get('stack', [])
                dev_techs = [t.lower() for t in developer.get('technologies', [])]
                dev_exp = developer.get('experience_years', 0)
                
                # Calculate match score
                score = 0
                
                # Technology matching (highest priority)
                tech_matches = sum(1 for tag in task_tags if tag.lower() in dev_techs)
                score += tech_matches * 10
                
                # Stack matching (backend/frontend)
                if 'backend' in task_type and 'backend' in dev_stack:
                    score += 5
                elif 'frontend' in task_type and 'frontend' in dev_stack:
                    score += 5
                
                # Experience points
                score += dev_exp
                
                # Work history bonus (prefer developers with related experience)
                if dev_email in work_history:
                    history = work_history[dev_email]
                    if task_type in history.get('issue_types', {}):
                        score += 3
                
                # Workload balancing (prefer less loaded developers)
                score -= developer_workload[dev_email] * 0.5
                
                # Update best match
                if score > best_score:
                    best_score = score
                    best_match = dev_email
            
            # Assign task to best match
            if best_match:
                assignments.append({
                    'task_id': task['id'],
                    'assignee': best_match,
                    'summary': task['summary'],
                    'issue_type': task['issue_type'],
                    'story_points': task.get('story_points', 0)
                })
                developer_workload[best_match] += task.get('story_points', 1)
        
        logging.info(f"Successfully assigned {len(assignments)} tasks")
        return assignments
    
    except Exception as e:
        logging.error(f"Error in assign_tasks_to_developers: {str(e)}")
        return []
# Example usage:
if __name__ == "__main__":
    # Example: Get all developers for each project
    tenant = "sliit"
    tenant_db = "agilemind_db"
    
    # Get all projects
    print("Fetching all projects...")
    projects = get_all_project(tenant)
    
    print(f"\nFound {len(projects)} project(s)\n")
    print("=" * 80)
    
    # For each project, get the developers
    for project in projects:
        project_id = str(project['project_id'])
        project_name = project.get('project_name', 'Unknown')
        
        print(f"\nProject: {project_name} (ID: {project_id})")
        print("-" * 80)
        
        # Get developers for this project
        developers = get_developers(tenant, project_id)
        
        print(f"Found {len(developers)} developer(s):")
        for dev in developers:
            print(f"  - {dev['email']}")
            print(f"    Stack: {dev['stack']}")
            print(f"    Technologies: {dev['technologies']}")
            print(f"    Experience: {dev['experience_years']} years")
            print()
