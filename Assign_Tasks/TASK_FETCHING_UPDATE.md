# Task Fetching Method Update - Change Log

## Summary

Updated `ai_assignee.py` to use the **exact same task fetching logic** as the original `assignee.py`. This ensures consistency between both systems when retrieving tasks for assignment.

## Changes Made

### 1. Added `get_unassigned_parent_tasks()` Method

This method replicates the exact logic from `assignee.py`:

```python
def get_unassigned_parent_tasks(self, project_id: int) -> List[str]:
    """
    Get parent backlog items that don't have a sprint assigned (sprint_id IS NULL).
    Uses the same logic as the original assignee.py
    """
```

**What it does:**
- Checks if `project_backlog_priority` table exists
- Fetches parent task IDs where `sprint_id IS NULL`
- Orders by rank
- Returns list of backlog IDs

### 2. Added `get_subtasks_by_parent_ids()` Method

This method replicates the exact logic from `assignee.py`:

```python
def get_subtasks_by_parent_ids(self, parent_ids: List[str]) -> List[Dict]:
    """
    Get all subtasks where parent_task_id matches the given parent IDs.
    Uses the same logic as the original assignee.py
    """
```

**What it does:**
- Takes list of parent task IDs
- Fetches all subtasks with `status = 'todo'`
- Orders by priority DESC, story_points DESC
- Parses JSON tags
- Returns list of subtask dictionaries

### 3. Updated `get_unassigned_tasks()` Method

Now uses the two methods above to fetch tasks in the same way as `assignee.py`:

```python
def get_unassigned_tasks(self, project_id: int) -> List[Dict]:
    """
    Fetch unassigned tasks using the same method as original assignee.py.
    Gets parent tasks from project_backlog_priority, then fetches their subtasks.
    """
```

**Process:**
1. Get unassigned parent tasks from `project_backlog_priority`
2. Get subtasks for those parent tasks
3. Filter to only include tasks without assignees
4. Format for AI assignment system

## Key Differences from Previous Version

### Before (Old AI Method)
```python
# Directly queried subtasks with assignee filter
subtask_query = """
    SELECT ... FROM project_backlog
    WHERE parent_task_id IN (...)
        AND status = 'todo'
        AND (assignee IS NULL OR assignee = '')  # ← Filter here
"""
```

### After (New Method - Matches Original)
```python
# Step 1: Get parent tasks from priority table
parent_task_ids = self.get_unassigned_parent_tasks(project_id)

# Step 2: Get ALL subtasks (including assigned ones)
subtasks = self.get_subtasks_by_parent_ids(parent_task_ids)

# Step 3: Filter unassigned in Python
for task in subtasks:
    if not task.get('assignee') or task.get('assignee') == '':
        tasks.append(formatted_task)  # ← Filter here
```

## Benefits

### ✅ Consistency
Both systems now fetch tasks using identical logic, ensuring:
- Same parent task selection
- Same subtask retrieval
- Same ordering (priority DESC, story_points DESC)

### ✅ Compatibility
- Works with existing database structure
- Uses same table joins and filters
- Maintains same error handling

### ✅ Maintainability
- Single source of truth for task fetching logic
- Easier to debug when both systems behave identically
- Changes to task fetching can be applied to both systems

## Database Flow

```
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: Get Unassigned Parent Tasks                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Table: project_backlog_priority                            │
│  Filter: project_id = X AND sprint_id IS NULL               │
│  Order: rank                                                 │
│  Result: List of parent backlog_ids                         │
│                                                              │
│  Example: ['TAM-48', 'TAM-52', 'TAM-55']                    │
│                                                              │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: Get Subtasks for Parent Tasks                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Table: project_backlog                                     │
│  Filter: parent_task_id IN ('TAM-48', 'TAM-52', 'TAM-55')   │
│          AND status = 'todo'                                 │
│  Order: priority DESC, story_points DESC                     │
│  Result: All subtasks (including assigned ones)             │
│                                                              │
│  Example:                                                    │
│    - TAM-48-1 (assignee: NULL)         ← Will be assigned   │
│    - TAM-48-2 (assignee: dev@email)    ← Skip (assigned)    │
│    - TAM-52-1 (assignee: NULL)         ← Will be assigned   │
│                                                              │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 3: Filter Unassigned Tasks                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Python Filter: assignee IS NULL OR assignee = ''           │
│  Result: Only unassigned subtasks ready for AI assignment   │
│                                                              │
│  Example:                                                    │
│    - TAM-48-1 (ready for assignment)                        │
│    - TAM-52-1 (ready for assignment)                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Example Usage

### Original System (assignee.py)
```python
# Step 1
parent_task_ids = get_unassigned_parent_tasks(project_id, tenant)

# Step 2
subtasks = get_subtasks_by_parent_ids(parent_task_ids, tenant_db)

# Step 3 (implicit in assign_tasks_to_developers)
for task in subtasks:
    # Assign to developers...
```

### New AI System (ai_assignee.py) - Now Identical
```python
# Step 1
parent_task_ids = self.get_unassigned_parent_tasks(project_id)

# Step 2
subtasks = self.get_subtasks_by_parent_ids(parent_task_ids)

# Step 3
tasks = [task for task in subtasks if not task.get('assignee')]

# Step 4 - AI Assignment
assignments = self.assign_with_ai(tasks, developers, project_id)
```

## Testing

To verify both systems fetch the same tasks:

```python
from assignee import get_unassigned_parent_tasks, get_subtasks_by_parent_ids
from ai_assignee import AITaskAssigner

# Original system
parent_ids_old = get_unassigned_parent_tasks(10237, "sliit")
subtasks_old = get_subtasks_by_parent_ids(parent_ids_old, "sliit")

# New AI system
ai_assigner = AITaskAssigner("sliit", "agilemind_db")
parent_ids_new = ai_assigner.get_unassigned_parent_tasks(10237)
subtasks_new = ai_assigner.get_subtasks_by_parent_ids(parent_ids_new)

# Compare
print(f"Parent IDs match: {parent_ids_old == parent_ids_new}")
print(f"Subtask count match: {len(subtasks_old) == len(subtasks_new)}")
```

## Impact on AI Assignment

### No Change to AI Logic
The AI scoring and assignment logic remains unchanged:
- ✅ Skill matching
- ✅ History analysis
- ✅ Workload balancing
- ✅ TF-IDF similarity
- ✅ Naive Bayes prediction
- ✅ Confidence scoring

### Only Change: Task Input
- **Before**: Tasks fetched with custom query
- **After**: Tasks fetched using original assignee.py logic
- **Result**: Same tasks, same AI processing, same quality assignments

## Backward Compatibility

✅ **Fully Compatible** - No breaking changes:
- Database schema unchanged
- API unchanged
- Output format unchanged
- Confidence scoring unchanged

## Migration Notes

If you're already using the AI system:
1. No action required - update is transparent
2. Task fetching now matches original system exactly
3. All existing functionality preserved
4. Can run comparison tool to verify consistency

## Files Modified

- ✅ `ai_assignee.py` - Updated task fetching methods

## Files Unchanged

- ✅ `assignee.py` - Original system (reference)
- ✅ `compare_systems.py` - Comparison tool
- ✅ `database.py` - Database utilities
- ✅ All documentation files

## Conclusion

The AI assignment system now uses **identical task fetching logic** as the original `assignee.py`, ensuring:
- Consistent behavior across both systems
- Same task selection criteria
- Easier comparison and validation
- Simplified maintenance

The AI enhancement remains fully intact while ensuring compatibility with the proven task retrieval method.

---

**Updated**: 2026-02-07  
**Version**: 1.1  
**Status**: Production Ready
