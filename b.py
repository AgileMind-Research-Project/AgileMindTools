from splittask import split_task

backlog=[
  {
    "project_id": 1,
    "id": 1001,
    "name": "Project initialization & repo setup",
    "description": "Create repository structure, branch strategy, README, CODEOWNERS, and initial license.",
    "issue_type": "task",
    "status": "todo",
    "priority": "high",
    "assignee": None,
    "story_points": 5,
    "sprint": None,
    "tags": ["devops","setup","documentation"]
  },{
    "project_id": 1,
    "id": 2001,
    "name": "Login fails with valid credentials",
    "description": "Users cannot log in even with correct username and password.",
    "issue_type": "bug",
    "status": "todo",
    "priority": "high",
    "severity": "critical",
    "assignee": None,
    "story_points": 5,
    "sprint": None,
    "tags": ["auth", "login", "production"]
  },
  {
    "project_id": 1,
    "id": 2002,
    "name": "Password reset email not sent",
    "description": "Password reset emails are not delivered to users.",
    "issue_type": "bug",
    "status": "todo",
    "priority": "high",
    "severity": "major",
    "assignee": None,
    "story_points": 3,
    "sprint": None,
    "tags": ["auth", "email"]
  },
  {
    "project_id": 1,
    "id": 2003,
    "name": "User session expires too early",
    "description": "User sessions expire within minutes instead of configured duration.",
    "issue_type": "bug",
    "status": "todo",
    "priority": "medium",
    "severity": "major",
    "assignee": None,
    "story_points": 3,
    "sprint": None,
    "tags": ["session", "security"]
  },
  {
    "project_id": 1,
    "id": 2004,
    "name": "Project list not loading",
    "description": "Projects page shows blank screen for some users.",
    "issue_type": "bug",
    "status": "todo",
    "priority": "high",
    "severity": "critical",
    "assignee": None,
    "story_points": 5,
    "sprint": None,
    "tags": ["ui", "project"]
  }
]


# Process backlog items and generate subtasks
if __name__ == "__main__":
    print("=" * 70)
    print("BACKLOG TASK SPLITTING - Using split_task method from splittask.py")
    print("=" * 70)
    
    all_subtasks = []
    
    for item in backlog:
        if item["issue_type"] == "task":  # Only split tasks, not bugs
            print(f"\n[TASK] Processing: {item['name']}")
            print(f"   Story Points: {item['story_points']}")
            
            subtasks = split_task(item)
            
            if subtasks:
                print(f"   [OK] Generated {len(subtasks)} subtasks:")
                for i, subtask in enumerate(subtasks, 1):
                    print(f"      {i}. {subtask['title']} (SP: {subtask['story_points']})")
                    all_subtasks.append(subtask)
            else:
                print(f"   [WARNING] No subtasks generated")
        else:
            print(f"\n[BUG] Skipping bug: {item['name']}")
    
    print(f"\n{'=' * 70}")
    print(f"Total subtasks generated: {len(all_subtasks)}")
    print(f"{'=' * 70}")
