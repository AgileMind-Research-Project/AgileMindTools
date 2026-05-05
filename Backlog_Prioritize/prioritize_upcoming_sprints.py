"""
AWS Lambda function to prioritize backlog items for projects with upcoming sprints.
This function integrates:
- get_upcoming_sprint_items.py - Retrieves projects with sprints starting in 4 days
- Backlog_prioritize.py - Runs ML-based WSJF prioritization
- Database storage - Saves priority rankings to project_backlog_priority table
"""

from database import read_from_mysql_with_params, execute_query
from keys import get_credential
from get_upcoming_sprint_items import get_upcoming_sprint_backlog
from Backlog_prioritize import train_and_prioritize
import logging
import json
import pandas as pd
from datetime import datetime
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Path to historical training data (use absolute path relative to this script)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORICAL_CSV_PATH = os.path.join(SCRIPT_DIR, 'GFG_FINAL.csv')


def transform_backlog_to_priority_format(backlog_items, project_id):
    """
    Transform database backlog items to the format used by b.py for ML prioritization.
    
    Args:
        backlog_items: List of backlog item dictionaries from database
        project_id: Project ID
    
    Returns:
        List of backlog items in b.py format
    """
    try:
        transformed_items = []
        
        for item in backlog_items:
            # Parse tags from JSON string to list
            tags = []
            if item.get('tags'):
                try:
                    if isinstance(item['tags'], str):
                        tags = json.loads(item['tags'])
                    elif isinstance(item['tags'], list):
                        tags = item['tags']
                except:
                    tags = []
            
            # Map issue_type: if it's 'task' or anything else not in standard types, keep it
            # Database stores: story, feature, change, bug
            issue_type = item.get('issue_type', 'story')
            if issue_type not in ['story', 'feature', 'change', 'bug']:
                issue_type = 'story'  # Default to story for unknown types
            
            # Create transformed item
            transformed_item = {
                'project_id': project_id,
                'id': item.get('id'),  # Keep Jira ID like "AMNT-1"
                'name': item.get('summary', ''),
                'description': item.get('description', ''),
                'issue_type': issue_type,
                'status': item.get('status', 'todo'),
                'priority': item.get('priority', 'medium'),
                'assignee': item.get('assignee'),
                'story_points': item.get('story_points') if item.get('story_points') and item.get('story_points') > 0 else (item.get('story_point_estimate') if item.get('story_point_estimate') and item.get('story_point_estimate') > 0 else 3),
                'sprint': None,
                'tags': tags
            }
            
            # Add severity for bugs
            if item.get('severity'):
                transformed_item['severity'] = item['severity']
            
            transformed_items.append(transformed_item)
        
        logger.info(f"Transformed {len(transformed_items)} backlog items for project {project_id}")
        return transformed_items
        
    except Exception as e:
        logger.error(f"Error transforming backlog items: {str(e)}")
        raise


def get_historical_training_data(tenant, project_id=None):
    """
    Fetch historical backlog priority data from database for PCA training.
    Only includes records where sprint_id IS NOT NULL (completed/assigned sprints).
    
    Args:
        tenant: Tenant name/database schema
        project_id: Optional - Filter historical data by specific project_id
                   If None, retrieves data from ALL projects (cross-project training)
    
    Returns:
        DataFrame with historical data in GFG_FINAL.csv format, or empty DataFrame if no data
    """
    try:
        print("\n" + "="*80)
        print("🗄️  LOADING HISTORICAL TRAINING DATA FROM DATABASE")
        print("="*80)
        logger.info("Fetching historical training data from database...")
        print(f"Tenant: {tenant}")
        
        if project_id:
            print(f"Project Filter: {project_id} (Project-Specific Training)")
        else:
            print(f"Project Filter: NONE (Cross-Project Training)")
        
        print("Query: project_backlog_priority (WHERE sprint_id IS NOT NULL)")
        print("="*80)
        
        # Query to get historical prioritized backlog items
        # Join project_backlog_priority with project_backlog to get full item details
        if project_id:
            query = """
            SELECT 
                pb.id,
                pb.project_id,
                pb.summary,
                pb.description,
                pb.issue_type,
                pb.status,
                pb.priority,
                pb.severity,
                pb.assignee,
                pb.tags,
                pb.estimated_hours,
                pb.story_points,
                pb.story_point_estimate,
                pbp.rank as actual_completed_rank,
                pbp.sprint_id
            FROM project_backlog_priority pbp
            INNER JOIN project_backlog pb ON pbp.backlog_id = pb.id
            WHERE pbp.sprint_id IS NOT NULL
            AND pb.project_id = %(project_id)s
            ORDER BY pbp.project_id, pbp.rank
            """
            params = {'project_id': project_id}
        else:
            query = """
            SELECT 
                pb.id,
                pb.project_id,
                pb.summary,
                pb.description,
                pb.issue_type,
                pb.status,
                pb.priority,
                pb.severity,
                pb.assignee,
                pb.tags,
                pb.estimated_hours,
                pb.story_points,
                pb.story_point_estimate,
                pbp.rank as actual_completed_rank,
                pbp.sprint_id
            FROM project_backlog_priority pbp
            INNER JOIN project_backlog pb ON pbp.backlog_id = pb.id
            WHERE pbp.sprint_id IS NOT NULL
            ORDER BY pbp.project_id, pbp.rank
            """
            params = {}
        
        df = read_from_mysql_with_params(query, params, tenant)
        
        if df.empty:
            if project_id:
                print(f"❌ No historical training data found for project {project_id}")
                logger.info(f"No historical training data found for project {project_id}")
            else:
                print("❌ No historical training data found (sprint_id IS NOT NULL)")
                logger.info("No historical training data found in database (sprint_id IS NOT NULL)")
            return pd.DataFrame()
        
        print(f"\n✅ Retrieved {len(df)} historical records from database")
        
        # Show project breakdown
        project_summary = df.groupby('project_id').agg({
            'id': 'count',
            'priority': lambda x: x.value_counts().to_dict(),
            'severity': lambda x: x.value_counts().to_dict()
        }).rename(columns={'id': 'count'})
        
        print(f"\n📋 Project Breakdown:")
        for proj_id, row in project_summary.iterrows():
            print(f"   Project {proj_id}: {int(row['count'])} records")
            print(f"      Priority: {row['priority']}")
            print(f"      Severity: {row['severity']}")
        
        print("\n" + "="*80)
        logger.info(f"Fetched {len(df)} historical records from database")
        
        # Transform to GFG_FINAL.csv format
        # Map 'summary' to 'name' for compatibility with PCA training
        df['name'] = df['summary']
        
        # Parse tags from JSON to string format
        def parse_tags(tags):
            if pd.isna(tags) or tags is None:
                return ''
            try:
                if isinstance(tags, str):
                    tags_list = json.loads(tags)
                    if isinstance(tags_list, list):
                        return ' '.join(tags_list)
                elif isinstance(tags, list):
                    return ' '.join(tags)
                return str(tags)
            except:
                return ''
        
        df['tags'] = df['tags'].apply(parse_tags)
        
        # Fill NaN values for text fields
        df['description'] = df['description'].fillna('')
        df['tags'] = df['tags'].fillna('')
        
        # Ensure priority and severity are in correct format
        # Priority: high, medium, low
        df['priority'] = df['priority'].fillna('medium').str.lower()
        
        # Severity: blocker, critical, major, minor, trivial
        if 'severity' in df.columns:
            df['severity'] = df['severity'].fillna('major').str.lower()
        else:
            df['severity'] = 'major'
        
        # Ensure story_points has valid values - fallback to story_point_estimate
        df['story_points'] = df.apply(
            lambda r: r['story_points'] if pd.notna(r['story_points']) and r['story_points'] > 0 
            else (r['story_point_estimate'] if pd.notna(r['story_point_estimate']) and r['story_point_estimate'] > 0 else 3),
            axis=1
        )
        
        logger.info(f"Transformed {len(df)} database records to training format")
        logger.info(f"Columns available: {df.columns.tolist()}")
        
        return df
        
    except Exception as e:
        logger.error(f"Error fetching historical training data: {str(e)}")
        return pd.DataFrame()





def get_or_create_sprint(project_id, next_sprint_start_date, sprint_size, tenant):
    """
    Get or create a sprint for the upcoming sprint start date.
    
    Args:
        project_id: Project ID
        next_sprint_start_date: Start date of the next sprint
        sprint_size: Sprint size in weeks
        tenant: Tenant name/database schema
    
    Returns:
        sprint_id of the existing or newly created sprint, or None if failed
    """
    try:
        from datetime import timedelta
        
        # First, try to find an existing sprint
        check_query = """
        SELECT sprint_id 
        FROM sprint 
        WHERE project_id = %(project_id)s 
        AND start_date = %(start_date)s
        LIMIT 1
        """
        
        sprint_df = read_from_mysql_with_params(
            check_query,
            {
                'project_id': project_id,
                'start_date': next_sprint_start_date
            },
            tenant
        )
        
        if not sprint_df.empty:
            sprint_id = sprint_df.iloc[0]['sprint_id']
            logger.info(f"Found existing sprint_id: {sprint_id} for project {project_id}")
            return int(sprint_id)
        
        # If no sprint exists, create one
        logger.info(f"Creating new sprint for project {project_id} starting on {next_sprint_start_date}")
        
        # Convert next_sprint_start_date to date object if it's a string
        if isinstance(next_sprint_start_date, str):
            from datetime import datetime as dt
            next_sprint_start_date = dt.strptime(next_sprint_start_date, '%Y-%m-%d').date()
        elif hasattr(next_sprint_start_date, 'date'):
            next_sprint_start_date = next_sprint_start_date.date()
        
        # Calculate end date based on sprint_size (in weeks)
        end_date = next_sprint_start_date + timedelta(weeks=sprint_size if sprint_size else 2)
        
        # Get the next sprint_id (max + 1)
        max_sprint_query = """
        SELECT COALESCE(MAX(sprint_id), 0) as max_id FROM sprint
        """
        max_sprint_df = read_from_mysql_with_params(max_sprint_query, {}, tenant)
        
        if not max_sprint_df.empty:
            next_sprint_id = int(max_sprint_df.iloc[0]['max_id']) + 1
        else:
            next_sprint_id = 1
        
        logger.info(f"Generating new sprint_id: {next_sprint_id}")
        
        # Generate sprint name based on start date
        sprint_name = f"Sprint starting {next_sprint_start_date}"
        
        insert_sprint_query = """
        INSERT INTO sprint (sprint_id, project_id, sprint_name, start_date, end_date)
        VALUES (:sprint_id, :project_id, :sprint_name, :start_date, :end_date)
        """
        
        result = execute_query(
            insert_sprint_query,
            {
                'sprint_id': next_sprint_id,
                'project_id': project_id,
                'sprint_name': sprint_name,
                'start_date': str(next_sprint_start_date),
                'end_date': str(end_date)
            },
            tenant
        )
        
        if result:
            # Get the newly created sprint_id
            sprint_df = read_from_mysql_with_params(
                check_query,
                {
                    'project_id': project_id,
                    'start_date': next_sprint_start_date
                },
                tenant
            )
            
            if not sprint_df.empty:
                sprint_id = sprint_df.iloc[0]['sprint_id']
                logger.info(f"Created new sprint_id: {sprint_id} for project {project_id}")
                return int(sprint_id)
        
        logger.error(f"Failed to create sprint for project {project_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error in get_or_create_sprint: {str(e)}")
        return None


def save_priorities_to_database(project_id, prioritized_df, tenant, sprint_id=None, prioritize_task_count=15):
    """
    Save prioritized backlog items to project_backlog_priority table.
    Only saves top ranked items based on prioritize_task_count (default: 15).
    
    Args:
        project_id: Project ID
        prioritized_df: DataFrame with prioritized backlog items
        tenant: Tenant name/database schema
        sprint_id: Sprint ID to assign
        prioritize_task_count: Number of top items to save (comes from projects table)
    
    Returns:
        Number of items saved
    """
    try:
        if prioritized_df.empty:
            logger.info("No items to save")
            return 0
        
        # Use prioritize_task_count for filtering (default to 15 if None)
        task_limit = prioritize_task_count if prioritize_task_count is not None else 15
        
        # Filter only top ranked items
        top_df = prioritized_df[prioritized_df['priority_rank'] <= task_limit].copy()
        
        if top_df.empty:
            logger.info(f"No items in rank 1-{task_limit} range")
            return 0
        
        logger.info(f"Filtered {len(top_df)} items with rank 1-{task_limit} from {len(prioritized_df)} total items")
        
        # Create CSV file with top ranked items
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f"project_{project_id}_top{task_limit}_priority_{timestamp}.csv"
        csv_path = os.path.join(SCRIPT_DIR, csv_filename)
        
        # Select relevant columns for CSV export
        csv_columns = ['priority_rank', 'id', 'name', 'description', 'issue_type', 
                      'priority', 'status', 'story_points', 'WSJF', 'moscow_category', 'assignee']
        
        # Filter columns that exist in the dataframe
        available_columns = [col for col in csv_columns if col in top_df.columns]
        csv_df = top_df[available_columns].copy()
        
        # Save to CSV
        csv_df.to_csv(csv_path, index=False, encoding='utf-8')
        logger.info(f"Created CSV file: {csv_filename}")
        
        # INSERT query - always includes sprint_id
        insert_query = """
        INSERT INTO project_backlog_priority 
        (project_id, backlog_id, `rank`, sprint_id)
        VALUES 
        (:project_id, :backlog_id, :rank, :sprint_id)
        ON DUPLICATE KEY UPDATE
            `rank` = VALUES(`rank`),
            sprint_id = VALUES(sprint_id),
            updated_at = CURRENT_TIMESTAMP
        """
        
        success_count = 0
        
        # Only save top ranked items to database
        for _, row in top_df.iterrows():
            try:
                # Prepare data for insertion with sprint_id
                data = {
                    'project_id': project_id,
                    'backlog_id': row['id'],  # Jira issue key like "AMNT-1"
                    'rank': int(row['priority_rank']),
                    'sprint_id': sprint_id
                }
                
                result = execute_query(insert_query, data, tenant)
                if result:
                    success_count += 1
                    
            except Exception as e:
                logger.error(f"Error inserting priority for item {row.get('id')}: {str(e)}")
                continue
        
        logger.info(f"Successfully saved {success_count} priority rankings (top {task_limit}) for project {project_id}")
        
        # After saving priorities, create notification for project managers
        logger.info(f"Attempting to create notification for project {project_id}")
        create_notification_for_project_managers(project_id, success_count, tenant)
        
        return success_count
        
    except Exception as e:
        logger.error(f"Error in save_priorities_to_database: {str(e)}")
        raise


def create_notification_for_project_managers(project_id, items_count, tenant):
    """
    Create a notification for project managers when backlog prioritization is completed.
    Directly inserts into notifications table.
    
    Args:
        project_id: Project ID
        items_count: Number of items prioritized
        tenant: Tenant database name
    """
    try:
        logger.info(f"[NOTIFICATION] Starting notification creation for project {project_id}")
        
        # Get project details and project managers
        project_query = """
        SELECT project_name, project_manager
        FROM projects
        WHERE project_id = %(project_id)s
        """
        
        logger.info(f"[NOTIFICATION] Querying project details from database")
        project_df = read_from_mysql_with_params(
            project_query,
            {'project_id': project_id},
            tenant
        )
        
        if project_df.empty:
            logger.warning(f"[NOTIFICATION] Project {project_id} not found in database")
            return
        
        project_name = project_df.iloc[0]['project_name']
        project_manager = project_df.iloc[0].get('project_manager')
        
        logger.info(f"[NOTIFICATION] Project name: {project_name}")
        logger.info(f"[NOTIFICATION] Project manager raw value: {project_manager}")
        
        # Parse project_manager JSON to get list of emails
        project_manager_emails = []
        if project_manager:
            try:
                if isinstance(project_manager, str):
                    project_manager_emails = json.loads(project_manager)
                    logger.info(f"[NOTIFICATION] Parsed project_manager from JSON string: {project_manager_emails}")
                elif isinstance(project_manager, list):
                    project_manager_emails = project_manager
                    logger.info(f"[NOTIFICATION] Project_manager is already a list: {project_manager_emails}")
            except Exception as e:
                logger.error(f"[NOTIFICATION] Error parsing project_manager: {str(e)}")
        else:
            logger.warning(f"[NOTIFICATION] project_manager field is NULL or empty")
        
        if not project_manager_emails:
            logger.warning(f"[NOTIFICATION] No project managers assigned to project {project_id}, skipping notification")
            return
        
        # Create notification directly in database
        notification_header = f"Backlog Prioritized for {project_name}"
        notification_description = f"The backlog for project '{project_name}' has been prioritized. {items_count} items have been ranked and are ready for your review."
        notification_type = "SUCCESS"
        
        # Convert project_manager_emails to JSON string for database
        related_users_json = json.dumps(project_manager_emails)
        
        logger.info(f"[NOTIFICATION] Creating notification in database")
        logger.info(f"   Header: {notification_header}")
        logger.info(f"   Type: {notification_type}")
        logger.info(f"   Recipients: {project_manager_emails}")
        
        # Insert notification into database
        insert_notification_query = """
        INSERT INTO notifications (
            header,
            description,
            related_users,
            notification_type,
            is_read,
            created_at,
            updated_at
        ) VALUES (
            :header,
            :description,
            :related_users,
            :notification_type,
            FALSE,
            NOW(),
            NOW()
        )
        """
        
        result = execute_query(
            insert_notification_query,
            {
                'header': notification_header,
                'description': notification_description,
                'related_users': related_users_json,
                'notification_type': notification_type
            },
            tenant
        )
        
        if result:
            logger.info(f"✅ [NOTIFICATION] Successfully created notification for {len(project_manager_emails)} project manager(s)")
        else:
            logger.error(f"❌ [NOTIFICATION] Failed to insert notification into database")
            
    except Exception as e:
        logger.error(f"❌ [NOTIFICATION] Exception in create_notification_for_project_managers: {str(e)}")
        logger.exception(e)
        raise


def run_prioritization_for_project(project_data, historical_csv_path, tenant):
    """
    Run ML-based prioritization for a single project.
    
    Args:
        project_data: Project dictionary with backlog_items
        historical_csv_path: Path to historical training CSV
        tenant: Tenant name/database schema
    
    Returns:
        Dictionary with prioritization results
    """
    try:
        project_id = project_data['project_id']
        project_name = project_data['project_name']
        backlog_items = project_data.get('backlog_items', [])
        next_sprint_start_date = project_data.get('next_sprint_start_date')
        sprint_size = project_data.get('sprint_size', 2)  # Default to 2 weeks
        
        if not backlog_items:
            logger.info(f"No backlog items for project {project_name}")
            return {
                'project_id': project_id,
                'project_name': project_name,
                'items_prioritized': 0,
                'items_saved': 0
            }
        
        logger.info(f"Running prioritization for project: {project_name} ({project_id})")
        
        # Transform backlog items to b.py format
        transformed_backlog = transform_backlog_to_priority_format(backlog_items, project_id)
        
        # Fetch historical training data from database (sprint_id IS NOT NULL)
        # Filtered by PROJECT_ID for project-specific training
        logger.info(f"Fetching historical training data for project {project_id}...")
        historical_db_data = get_historical_training_data(tenant, project_id=project_id)
        
        # PCA requires minimum 3 samples for n_components=3
        MIN_HISTORICAL_RECORDS = 3
        
        print("\n" + "="*80)
        print(f"🎯 PROJECT: {project_name} ({project_id})")
        print(f"📦 Backlog Items to Prioritize: {len(transformed_backlog)}")
        print("="*80)
        
        # Run ML-based prioritization with exclusive data source logic
        # If DB data exists AND has enough samples, use ONLY DB data; otherwise fall back to CSV
        if not historical_db_data.empty and len(historical_db_data) >= MIN_HISTORICAL_RECORDS:
            print(f"\n✅ USING DATABASE HISTORICAL DATA (Project-Specific)")
            print(f"   Project: {project_id}")
            print(f"   Records: {len(historical_db_data)}")
            print(f"   Min Required: {MIN_HISTORICAL_RECORDS}")
            logger.info(f"[DB DATA] Using {len(historical_db_data)} historical records from database for project {project_id}")
            prioritized_df = train_and_prioritize(
                historical_csv_path=historical_csv_path,
                backlog_items=transformed_backlog,
                additional_historical_df=historical_db_data
            )
        else:
            if not historical_db_data.empty:
                print(f"\n⚠️  INSUFFICIENT DATABASE DATA (Project-Specific)")
                print(f"   Project: {project_id}")
                print(f"   Found: {len(historical_db_data)} records")
                print(f"   Required: {MIN_HISTORICAL_RECORDS} minimum")
                logger.warning(f"[INSUFFICIENT DB DATA] Found {len(historical_db_data)} database records for project {project_id}, but PCA requires minimum {MIN_HISTORICAL_RECORDS} samples")
            else:
                print(f"\n⚠️  NO DATABASE HISTORICAL DATA (Project-Specific)")
                print(f"   Project: {project_id}")
                print(f"   Falling back to CSV file")
            
            print(f"\n🔄 USING CSV FALLBACK")
            print(f"   File: {historical_csv_path}")
            logger.info(f"[CSV FALLBACK] Using CSV for training: {historical_csv_path}")
            prioritized_df = train_and_prioritize(
                historical_csv_path=historical_csv_path,
                backlog_items=transformed_backlog,
                additional_historical_df=None
            )
        
        # Save priorities to database (sprint_id will be NULL, added later when sprint starts)
        logger.info(f"Saving priorities to database using prioritize_task_count: {project_data.get('prioritize_task_count', 15)}")
        items_saved = save_priorities_to_database(
            project_id=project_id, 
            prioritized_df=prioritized_df, 
            tenant=tenant, 
            sprint_id=None,
            prioritize_task_count=project_data.get('prioritize_task_count')
        )
        
        print(f"\n✅ PRIORITIZATION RESULTS FOR {project_name}")
        print(f"   Total Prioritized: {len(prioritized_df)}")
        print(f"   Saved to Database: {items_saved}")
        print("="*80 + "\n")
        
        return {
            'project_id': project_id,
            'project_name': project_name,
            'items_prioritized': len(prioritized_df),
            'items_saved': items_saved,
            'top_5_items': prioritized_df[['priority_rank', 'name', 'issue_type', 'story_points', 'WSJF', 'moscow_category']].head(5).to_dict('records')
        }
        
    except Exception as e:
        logger.error(f"Error prioritizing project {project_data.get('project_name')}: {str(e)}")
        return {
            'project_id': project_data.get('project_id'),
            'project_name': project_data.get('project_name'),
            'error': str(e),
            'items_prioritized': 0,
            'items_saved': 0
        }


def prioritize_all_upcoming_sprints(tenant, days_before=4):
    """
    Main orchestrator function that prioritizes backlog for all projects with upcoming sprints.
    
    Args:
        tenant: Tenant name/database schema
        days_before: Number of days before next sprint start date (default: 4)
    
    Returns:
        Dictionary with complete prioritization results
    """
    try:
        logger.info(f"Starting prioritization for projects with sprints in {days_before} days")
        
        # Get all projects with upcoming sprints and their backlog items
        upcoming_data = get_upcoming_sprint_backlog(tenant, days_before)
        
        if not upcoming_data.get('success'):
            return {
                'success': False,
                'error': upcoming_data.get('error', 'Failed to retrieve upcoming sprint data')
            }
        
        projects = upcoming_data.get('projects', [])
        
        if not projects:
            return {
                'success': True,
                'message': f"No projects with sprints starting in {days_before} days",
                'target_date': upcoming_data.get('target_date'),
                'projects_processed': 0,
                'total_items_prioritized': 0,
                'total_items_saved': 0
            }
        
        # Process each project
        results = []
        total_prioritized = 0
        total_saved = 0
        
        print("\n" + "="*80)
        print(f"🚀 PROCESSING {len(projects)} PROJECT(S) FOR UPCOMING SPRINTS")
        print("="*80 + "\n")
        
        for idx, project in enumerate(projects, 1):
            print(f"[{idx}/{len(projects)}] Processing: {project.get('project_name')}")
            project_result = run_prioritization_for_project(
                project, 
                HISTORICAL_CSV_PATH, 
                tenant
            )
            results.append(project_result)
            total_prioritized += project_result.get('items_prioritized', 0)
            total_saved += project_result.get('items_saved', 0)
        
        print("\n" + "="*80)
        print("📊 PRIORITIZATION SUMMARY")
        print("="*80)
        print(f"Projects Processed: {len(results)}")
        print(f"Total Items Prioritized: {total_prioritized}")
        print(f"Total Items Saved to DB: {total_saved}")
        print("="*80 + "\n")
        
        return {
            'success': True,
            'target_date': upcoming_data.get('target_date'),
            'days_before': days_before,
            'projects_processed': len(results),
            'total_items_prioritized': total_prioritized,
            'total_items_saved': total_saved,
            'project_results': results
        }
        
    except Exception as e:
        logger.error(f"Error in prioritize_all_upcoming_sprints: {str(e)}")
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
        API Gateway compatible response with prioritization results
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
        
        # Run prioritization
        result = prioritize_all_upcoming_sprints(tenant, days_before)
        
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
    # Enable INFO logging to see detailed output
    logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
    
    # Test event
    test_event = {
        "tenant": "sliit",  # Change to your tenant name
        "days_before": 4
    }
    
    print("\n" + "="*80)
    print("AUTOMATED BACKLOG PRIORITIZATION FOR UPCOMING SPRINTS")
    print("="*80 + "\n")
    
    result = lambda_handler(test_event, None)
    
    # Extract and print results
    body = json.loads(result['body'])
    
    if body.get('success'):
        print(f"SUCCESS!")
        print(f"\nTarget Date: {body.get('target_date')}")
        print(f"Projects Processed: {body.get('projects_processed', 0)}")
        print(f"Total Items Prioritized: {body.get('total_items_prioritized', 0)}")
        print(f"Total Items Saved to DB: {body.get('total_items_saved', 0)}")
        
        if body.get('project_results'):
            print("\n" + "="*80)
            print("PROJECT PRIORITIZATION RESULTS")
            print("="*80)
            
            for project in body['project_results']:
                print(f"\n> {project['project_name']} (ID: {project['project_id']})")
                print(f"   Items Prioritized: {project.get('items_prioritized', 0)}")
                print(f"   Items Saved: {project.get('items_saved', 0)}")
                
                if project.get('top_5_items'):
                    print(f"\n   Top 5 Priority Items:")
                    for item in project['top_5_items']:
                        print(f"      #{item['priority_rank']} - {item['name'][:60]}")
                        print(f"         Type: {item['issue_type']} | SP: {item['story_points']} | WSJF: {item['WSJF']:.2f} | MoSCoW: {item['moscow_category']}")
                
                if project.get('error'):
                    print(f"   ERROR: {project['error']}")
        
        print("\n" + "="*80)
    else:
        print(f"ERROR: {body.get('error')}")
        print("\n" + "="*80)
