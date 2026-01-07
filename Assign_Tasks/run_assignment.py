# Intelligent Task Assignment Example
# Run this file to test the task assignment functionality

from assignee import assign_tasks_to_developers, get_all_project

# Configuration
TENANT_TABLE = "sliit"
TENANT_DB = "agilemind_db"

def main():
    """
    Main function to demonstrate intelligent task assignment.
    """
    print("=" * 80)
    print("INTELLIGENT TASK ASSIGNMENT SYSTEM")
    print("=" * 80)
    
    # Get all projects
    print("\n1. Fetching all projects...")
    projects = get_all_project(TENANT_TABLE)
    
    if not projects:
        print("No projects found!")
        return
    
    print(f"Found {len(projects)} project(s)\n")
    
    # For each project, perform intelligent task assignment
    for project in projects:
        project_id = project['project_id']
        project_name = project.get('project_name', 'Unknown')
        
        print(f"\n{'=' * 80}")
        print(f"Project: {project_name} (ID: {project_id})")
        print(f"{'=' * 80}\n")
        
        # Perform assignment
        assignments = assign_tasks_to_developers(
            project_id=project_id,
            tenant_table=TENANT_TABLE,
            tenant_db=TENANT_DB
        )
        
        if not assignments:
            print("No tasks to assign for this project.\n")
            continue
        
        # Display assignments
        print(f"\n✓ Assigned {len(assignments)} tasks:\n")
        print(f"{'Task ID':<15} {'Assignee':<35} {'Issue Type':<15} {'Story Points':<12} {'Summary'}")
        print("-" * 120)
        
        for assignment in assignments:
            task_id = assignment['task_id']
            assignee = assignment['assignee']
            issue_type = assignment['issue_type']
            story_points = assignment.get('story_points', 0)
            summary = assignment['summary'][:50] + "..." if len(assignment['summary']) > 50 else assignment['summary']
            
            print(f"{task_id:<15} {assignee:<35} {issue_type:<15} {story_points:<12} {summary}")
        
        # Display workload distribution
        print(f"\n\nWorkload Distribution:")
        print("-" * 80)
        workload = {}
        for assignment in assignments:
            email = assignment['assignee']
            points = assignment.get('story_points', 1)
            workload[email] = workload.get(email, 0) + points
        
        for email, points in sorted(workload.items(), key=lambda x: x[1], reverse=True):
            print(f"  {email:<35} {points:>3} points")
        
        print()

if __name__ == "__main__":
    main()
