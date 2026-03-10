"""
AWS Lambda function to generate Sprint Review presentations
and post them to project channels via Redis.

Flow:
1. Get all tenants from the database
2. For each tenant, get all projects
3. For each project, find the active sprint
4. Get sprint tasks from project_backlog table
5. Get sprint bugs from bugs table
6. Generate a sprint review presentation
7. Post the presentation to the project's channel via Redis
"""

from database import read_from_mysql_with_params, execute_query
from redis_client import RedisClient
import logging
import json
import os
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# System tables to exclude when detecting tenants
SYSTEM_TABLES = [
    'roles', 'password_reset_tokens', 'projects', 'sprint',
    'project_backlog', 'project_backlog_priority', 'bugs',
    'notifications', 'meetings', 'meeting_attendees',
    'meeting_transcripts', 'meeting_analysis', 'release_notes',
    'rag_documents', 'task_updates'
]


def get_all_tenants():
    """
    Get all tenant table names from the database.
    
    Returns:
        list: List of tenant table names
    """
    try:
        schema = os.getenv('DB_NAME', 'agilemind_db')
        query = "SHOW TABLES"
        result_df = read_from_mysql_with_params(query, {}, schema)

        if result_df.empty:
            logger.warning("No tables found in database")
            return []

        column_name = result_df.columns[0]
        all_tables = result_df[column_name].tolist()

        # Filter out system/shared tables — tenant tables are user-specific (e.g., 'sliit')
        tenants = [t for t in all_tables if t not in SYSTEM_TABLES]
        logger.info(f"Found {len(tenants)} tenant tables")
        return tenants

    except Exception as e:
        logger.error(f"Error getting tenants: {str(e)}")
        return []


def get_all_projects(tenant):
    """
    Get all projects for a tenant.
    
    Args:
        tenant: Tenant database schema name
    
    Returns:
        list: List of project dictionaries
    """
    try:
        query = """
        SELECT project_id, project_name, `key`, project_lead, project_manager
        FROM projects WHERE project_id ='10237'
        """
        df = read_from_mysql_with_params(query, {}, tenant)

        if df.empty:
            logger.info(f"No projects found for tenant {tenant}")
            return []

        return df.to_dict('records')

    except Exception as e:
        logger.error(f"Error getting projects for tenant {tenant}: {str(e)}")
        return []


def get_active_sprint(project_id, tenant):
    """
    Get the active sprint for a project.
    
    Args:
        project_id: Project ID
        tenant: Tenant database schema name
    
    Returns:
        dict: Sprint data or None if no active sprint
    """
    try:
        query = """
        SELECT sprint_id, sprint_name, start_date, end_date, sprint_status, sprint_goal
        FROM sprint
        WHERE project_id = %(project_id)s AND sprint_status = 'Active'
        ORDER BY start_date DESC
        LIMIT 1
        """
        df = read_from_mysql_with_params(query, {'project_id': project_id}, tenant)

        if df.empty:
            return None

        return df.iloc[0].to_dict()

    except Exception as e:
        logger.error(f"Error getting active sprint for project {project_id}: {str(e)}")
        return None


def get_sprint_tasks(sprint_id, tenant):
    """
    Get all backlog tasks for a sprint.
    
    Args:
        sprint_id: Sprint ID
        tenant: Tenant database schema name
    
    Returns:
        list: List of task dictionaries
    """
    try:
        query = """
        SELECT 
            id, summary, description, issue_type, status, priority,
            severity, assignee, story_points, estimated_hours, tags
        FROM project_backlog
        WHERE sprint_id = %(sprint_id)s
        ORDER BY priority DESC
        """
        df = read_from_mysql_with_params(query, {'sprint_id': sprint_id}, tenant)

        if df.empty:
            return []

        return df.to_dict('records')

    except Exception as e:
        logger.error(f"Error getting sprint tasks for sprint {sprint_id}: {str(e)}")
        return []


def get_sprint_bugs(project_id, sprint_id, tenant):
    """
    Get all bugs for a project's sprint.
    Joins bugs table with project_backlog to get bug details.
    
    Args:
        project_id: Project ID
        sprint_id: Sprint ID
        tenant: Tenant database schema name
    
    Returns:
        list: List of bug dictionaries with details
    """
    try:
        query = """
        SELECT 
            b.task_id,
            pb.summary,
            pb.description,
            pb.status,
            pb.priority,
            pb.severity,
            pb.assignee
        FROM bugs b
        LEFT JOIN project_backlog pb ON b.task_id = pb.id
        WHERE b.project_id = %(project_id)s AND b.sprint_id = %(sprint_id)s
        """
        df = read_from_mysql_with_params(
            query,
            {'project_id': project_id, 'sprint_id': sprint_id},
            tenant
        )

        if df.empty:
            return []

        return df.to_dict('records')

    except Exception as e:
        logger.error(f"Error getting sprint bugs for project {project_id}, sprint {sprint_id}: {str(e)}")
        return []


def generate_sprint_review_slides(project_name, project_key, sprint, tasks, bugs):
    """
    Generate sprint review as a list of PPT-style slides.
    Each slide is posted as a separate message to simulate a presentation.
    
    Args:
        project_name: Name of the project
        project_key: Project key (e.g., 'AMNT')
        sprint: Sprint data dictionary
        tasks: List of task dictionaries
        bugs: List of bug dictionaries
    
    Returns:
        list[str]: List of slide messages (each is a separate channel message)
    """
    sprint_name = sprint.get('sprint_name', 'Unknown Sprint')
    sprint_goal = sprint.get('sprint_goal', 'No sprint goal defined')
    start_date = sprint.get('start_date', '')
    end_date = sprint.get('end_date', '')

    # Categorize tasks by status
    completed_tasks = [t for t in tasks if str(t.get('status', '')).lower() in ('done', 'completed', 'closed')]
    in_progress_tasks = [t for t in tasks if str(t.get('status', '')).lower() in ('in progress', 'in_progress', 'active')]
    todo_tasks = [t for t in tasks if str(t.get('status', '')).lower() in ('todo', 'to do', 'open', 'new')]
    other_tasks = [t for t in tasks if t not in completed_tasks and t not in in_progress_tasks and t not in todo_tasks]

    # Calculate stats
    total_tasks = len(tasks)
    total_story_points = sum(t.get('story_points', 0) or 0 for t in tasks)
    completed_story_points = sum(t.get('story_points', 0) or 0 for t in completed_tasks)
    completion_rate = (len(completed_tasks) / total_tasks * 100) if total_tasks > 0 else 0

    slides = []

    # ── Slide 1: Title Slide ──
    slide1 = []
    slide1.append(f"📊 **SPRINT REVIEW**")
    slide1.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    slide1.append(f"")
    slide1.append(f"**{project_name}** ({project_key})")
    slide1.append(f"")
    slide1.append(f"🏃 Sprint: **{sprint_name}**")
    slide1.append(f"📅 Period: {start_date} → {end_date}")
    if sprint_goal:
        slide1.append(f"")
        slide1.append(f"🎯 Sprint Goal:")
        slide1.append(f"\"{sprint_goal}\"")
    slide1.append(f"")
    slide1.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    slide1.append(f"📑 Slide 1 of {{total_slides}}")
    slides.append("\n".join(slide1))

    # ── Slide 2: Sprint Summary / KPIs ──
    slide2 = []
    slide2.append(f"📈 **SPRINT SUMMARY**")
    slide2.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    slide2.append(f"")
    # Progress bar visualization
    filled = int(completion_rate / 5)  # 20 chars total
    bar = "█" * filled + "░" * (20 - filled)
    slide2.append(f"Completion: [{bar}] {completion_rate:.0f}%")
    slide2.append(f"")
    slide2.append(f"┌─────────────────────────────────┐")
    slide2.append(f"│  📋 Total Tasks:     {str(total_tasks).rjust(10)}  │")
    slide2.append(f"│  ✅ Completed:       {str(len(completed_tasks)).rjust(10)}  │")
    slide2.append(f"│  🔄 In Progress:     {str(len(in_progress_tasks)).rjust(10)}  │")
    slide2.append(f"│  📝 Todo:            {str(len(todo_tasks)).rjust(10)}  │")
    if other_tasks:
        slide2.append(f"│  ⚪ Other:           {str(len(other_tasks)).rjust(10)}  │")
    slide2.append(f"│  🐛 Bugs Found:      {str(len(bugs)).rjust(10)}  │")
    slide2.append(f"├─────────────────────────────────┤")
    slide2.append(f"│  🎯 Story Points:  {str(completed_story_points).rjust(4)}/{str(total_story_points).ljust(4)} SP  │")
    slide2.append(f"└─────────────────────────────────┘")
    slide2.append(f"")
    slide2.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    slide2.append(f"📑 Slide 2 of {{total_slides}}")
    slides.append("\n".join(slide2))

    # ── Slide 3: Completed Tasks ──
    if completed_tasks:
        slide3 = []
        slide3.append(f"✅ **COMPLETED TASKS ({len(completed_tasks)})**")
        slide3.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        slide3.append(f"")
        for i, t in enumerate(completed_tasks, 1):
            assignee = t.get('assignee', 'Unassigned') or 'Unassigned'
            sp = t.get('story_points', '-') or '-'
            priority = t.get('priority', '') or ''
            slide3.append(f"{i}. **[{t.get('id', '')}]** {t.get('summary', '')}")
            slide3.append(f"    👤 {assignee}  •  🎯 {sp} SP  •  ⚡ {priority}")
            slide3.append(f"")
        slide3.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        slide3.append(f"📑 Slide {{slide_num}} of {{total_slides}}")
        slides.append("\n".join(slide3))

    # ── Slide 4: In Progress Tasks ──
    if in_progress_tasks:
        slide4 = []
        slide4.append(f"🔄 **IN PROGRESS ({len(in_progress_tasks)})**")
        slide4.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        slide4.append(f"")
        for i, t in enumerate(in_progress_tasks, 1):
            assignee = t.get('assignee', 'Unassigned') or 'Unassigned'
            sp = t.get('story_points', '-') or '-'
            priority = t.get('priority', '') or ''
            slide4.append(f"{i}. **[{t.get('id', '')}]** {t.get('summary', '')}")
            slide4.append(f"    👤 {assignee}  •  🎯 {sp} SP  •  ⚡ {priority}")
            slide4.append(f"")
        slide4.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        slide4.append(f"📑 Slide {{slide_num}} of {{total_slides}}")
        slides.append("\n".join(slide4))

    # ── Slide 5: Not Started Tasks ──
    if todo_tasks:
        slide5 = []
        slide5.append(f"📋 **NOT STARTED ({len(todo_tasks)})**")
        slide5.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        slide5.append(f"")
        for i, t in enumerate(todo_tasks, 1):
            assignee = t.get('assignee', 'Unassigned') or 'Unassigned'
            sp = t.get('story_points', '-') or '-'
            priority = t.get('priority', '') or ''
            slide5.append(f"{i}. **[{t.get('id', '')}]** {t.get('summary', '')}")
            slide5.append(f"    👤 {assignee}  •  🎯 {sp} SP  •  ⚡ {priority}")
            slide5.append(f"")
        slide5.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        slide5.append(f"📑 Slide {{slide_num}} of {{total_slides}}")
        slides.append("\n".join(slide5))

    # ── Slide 6: Bugs Found ──
    if bugs:
        slide_bugs = []
        slide_bugs.append(f"🐛 **BUGS FOUND ({len(bugs)})**")
        slide_bugs.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        slide_bugs.append(f"")
        for i, b in enumerate(bugs, 1):
            severity = b.get('severity', 'Unknown') or 'Unknown'
            status = b.get('status', 'Open') or 'Open'
            assignee = b.get('assignee', 'Unassigned') or 'Unassigned'
            sev_icon = "🔴" if severity.lower() in ('critical', 'blocker') else "🟠" if severity.lower() in ('major', 'high') else "🟡" if severity.lower() == 'medium' else "🟢"
            slide_bugs.append(f"{i}. {sev_icon} **[{b.get('task_id', '')}]** {b.get('summary', 'No summary')}")
            slide_bugs.append(f"    Severity: {severity}  •  Status: {status}  •  👤 {assignee}")
            slide_bugs.append(f"")
        slide_bugs.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        slide_bugs.append(f"📑 Slide {{slide_num}} of {{total_slides}}")
        slides.append("\n".join(slide_bugs))

    # ── Final Slide: Thank You ──
    slide_end = []
    slide_end.append(f"🎬 **END OF SPRINT REVIEW**")
    slide_end.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    slide_end.append(f"")
    slide_end.append(f"**{project_name}** — {sprint_name}")
    slide_end.append(f"")
    slide_end.append(f"📊 {completion_rate:.0f}% Complete  •  {len(completed_tasks)}/{total_tasks} Tasks Done  •  {completed_story_points}/{total_story_points} SP")
    slide_end.append(f"")
    slide_end.append(f"Thank you for attending the Sprint Review! 🙏")
    slide_end.append(f"")
    slide_end.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    slide_end.append(f"🤖 Generated by AgileMind Sprint Review Bot")
    slide_end.append(f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    slide_end.append(f"📑 Slide {{slide_num}} of {{total_slides}}")
    slides.append("\n".join(slide_end))

    # Now fill in slide numbers
    total_slides = len(slides)
    numbered_slides = []
    for idx, slide in enumerate(slides, 1):
        numbered_slides.append(
            slide.replace("{total_slides}", str(total_slides))
                 .replace("{slide_num}", str(idx))
        )

    return numbered_slides


def create_notification(project_id, project_name, sprint_name, tenant):
    """
    Create a notification in the database for the sprint review post.
    
    Args:
        project_id: Project ID
        project_name: Project name
        sprint_name: Sprint name
        tenant: Tenant database schema
    """
    try:
        # Get project managers for notification
        pm_query = """
        SELECT project_manager FROM projects WHERE project_id = %(project_id)s
        """
        pm_df = read_from_mysql_with_params(pm_query, {'project_id': project_id}, tenant)

        if pm_df.empty:
            return

        project_manager = pm_df.iloc[0].get('project_manager')
        if not project_manager:
            return

        pm_emails = []
        if isinstance(project_manager, str):
            pm_emails = json.loads(project_manager)
        elif isinstance(project_manager, list):
            pm_emails = project_manager

        if not pm_emails:
            return

        insert_query = """
        INSERT INTO notifications (
            header, description, related_users, notification_type,
            is_read, created_at, updated_at
        ) VALUES (
            :header, :description, :related_users, :notification_type,
            FALSE, NOW(), NOW()
        )
        """

        execute_query(
            insert_query,
            {
                'header': f"Sprint Review Published — {project_name}",
                'description': f"Sprint review for '{sprint_name}' has been generated and posted to the project channel.",
                'related_users': json.dumps(pm_emails),
                'notification_type': 'INFO'
            },
            tenant
        )
        logger.info(f"Created notification for project {project_name}")

    except Exception as e:
        logger.error(f"Error creating notification: {str(e)}")


def process_project(project, tenant, redis_client):
    """
    Process a single project: get active sprint, tasks, bugs, generate review, post to channel.
    
    Args:
        project: Project dictionary
        tenant: Tenant name
        redis_client: RedisClient instance
    
    Returns:
        dict: Result summary
    """
    project_id = project['project_id']
    project_name = project['project_name']
    project_key = project.get('key', '')

    logger.info(f"Processing project: {project_name} ({project_id})")

    # Step 1: Get active sprint
    sprint = get_active_sprint(project_id, tenant)
    if not sprint:
        logger.info(f"No active sprint for project {project_name}, skipping")
        return {'project': project_name, 'status': 'skipped', 'reason': 'no_active_sprint'}

    sprint_id = sprint['sprint_id']
    sprint_name = sprint.get('sprint_name', 'Unknown')
    logger.info(f"Found active sprint: {sprint_name} (ID: {sprint_id})")

    # Step 2: Get sprint tasks
    tasks = get_sprint_tasks(sprint_id, tenant)
    logger.info(f"Found {len(tasks)} tasks in sprint")

    # Step 3: Get sprint bugs
    bugs = get_sprint_bugs(project_id, sprint_id, tenant)
    logger.info(f"Found {len(bugs)} bugs in sprint")

    if not tasks and not bugs:
        logger.info(f"No tasks or bugs found for sprint, skipping")
        return {'project': project_name, 'status': 'skipped', 'reason': 'no_data'}

    # Step 4: Generate sprint review slides (PPT-style)
    slides = generate_sprint_review_slides(
        project_name, project_key, sprint, tasks, bugs
    )
    logger.info(f"Generated {len(slides)} presentation slides")

    # Step 5: Find project channel in Redis and post each slide
    channel_id = redis_client.get_project_channel(tenant, project_id)

    posted = False
    if channel_id:
        all_sent = True
        for i, slide in enumerate(slides, 1):
            sent = redis_client.send_message(
                channel_id=channel_id,
                content=slide,
                username="Sprint Review Bot",
                user_id="system"
            )
            if sent:
                logger.info(f"✅ Sent slide {i}/{len(slides)} to channel {channel_id}")
            else:
                logger.error(f"❌ Failed to send slide {i}/{len(slides)}")
                all_sent = False
        posted = all_sent
        if posted:
            logger.info(f"✅ All {len(slides)} slides posted to channel {channel_id}")
    else:
        logger.warning(f"No channel found for project {project_name}, review not posted")

    # Step 6: Create notification
    create_notification(project_id, project_name, sprint_name, tenant)

    return {
        'project': project_name,
        'sprint': sprint_name,
        'status': 'success',
        'tasks_count': len(tasks),
        'bugs_count': len(bugs),
        'slides_count': len(slides),
        'channel_posted': posted,
        'channel_id': channel_id
    }


def lambda_handler(event, context):
    """
    AWS Lambda handler for Sprint Review generation.
    
    Iterates through all tenants and projects, generates sprint review
    presentations for active sprints, and posts them to project channels.
    
    Args:
        event: Lambda event (unused)
        context: Lambda context
    
    Returns:
        dict: Response with results summary
    """
    logger.info("=== Starting Sprint Review Generation ===")

    results = []
    redis_client = RedisClient()

    try:
        # Get all tenants
        tenants = get_all_tenants()

        if not tenants:
            logger.warning("No tenants found")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'No tenants found', 'results': []})
            }

        for tenant in tenants:
            if(tenant == 'sliit'):
                logger.info(f"\n--- Processing tenant: {tenant} ---")

                # Get all projects for this tenant
                projects = get_all_projects(tenant)

                if not projects:
                    logger.info(f"No projects for tenant {tenant}")
                    continue

                for project in projects:
                    try:
                        result = process_project(project, tenant, redis_client)
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Error processing project {project.get('project_name', '?')}: {str(e)}")
                        results.append({
                            'project': project.get('project_name', 'Unknown'),
                            'status': 'error',
                            'error': str(e)
                        })

    finally:
        redis_client.close()

    # Summary
    successful = [r for r in results if r.get('status') == 'success']
    skipped = [r for r in results if r.get('status') == 'skipped']
    errors = [r for r in results if r.get('status') == 'error']

    logger.info(f"\n=== Sprint Review Summary ===")
    logger.info(f"Total projects processed: {len(results)}")
    logger.info(f"Successful: {len(successful)}")
    logger.info(f"Skipped: {len(skipped)}")
    logger.info(f"Errors: {len(errors)}")

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'success': True,
            'summary': {
                'total': len(results),
                'successful': len(successful),
                'skipped': len(skipped),
                'errors': len(errors)
            },
            'results': results
        }, default=str)
    }


# For local testing
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    print("\n=== Running Sprint Review Generation (Local) ===\n")
    result = lambda_handler({}, None)
    print(json.dumps(json.loads(result['body']), indent=2))
