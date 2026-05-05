# Quick Start Guide - AI Task Assignment

## Installation

### 1. Install Required Dependencies

```bash
pip install numpy pandas sqlalchemy pymysql python-dotenv
```

### 2. Verify Database Configuration

Ensure your `.env` file contains:
```
DB_HOST=your_host
DB_PORT=3306
DB_USER=your_user
DB_PASSWORD=your_password
```

## Usage Examples

### Example 1: Basic AI Assignment

```python
from ai_assignee import AITaskAssigner

# Initialize
assigner = AITaskAssigner(
    tenant_table="sliit",
    tenant_db="agilemind_db"
)

# Run assignment and save to database
assignments = assigner.run_assignment(
    project_id=10237,
    save_to_db=True
)

# Print results
for assignment in assignments:
    print(f"{assignment['task_id']} -> {assignment['assignee']} ({assignment['confidence']:.1f}%)")
```

### Example 2: Dry Run (No Database Updates)

```python
from ai_assignee import AITaskAssigner

assigner = AITaskAssigner("sliit", "agilemind_db")

# Run without saving
assignments = assigner.run_assignment(
    project_id=10237,
    save_to_db=False  # Just preview assignments
)

# Review before committing
for a in assignments:
    if a['confidence'] >= 70:
        print(f"✓ High confidence: {a['task_id']} -> {a['assignee']}")
    else:
        print(f"⚠ Low confidence: {a['task_id']} -> {a['assignee']}")
```

### Example 3: Compare Old vs New System

```python
from compare_systems import AssignmentComparator

comparator = AssignmentComparator("sliit", "agilemind_db")
comparison = comparator.run_comparison(project_id=10237)

# Results show:
# - Which assignments changed
# - Confidence scores
# - Workload distribution
# - Recommendations
```

### Example 4: Access Detailed Scoring

```python
from ai_assignee import AITaskAssigner

assigner = AITaskAssigner("sliit", "agilemind_db")
assignments = assigner.run_assignment(10237, save_to_db=False)

# Analyze high-confidence assignments
for a in assignments:
    if a['confidence'] >= 80:
        print(f"\nTask: {a['summary']}")
        print(f"Assignee: {a['assignee']}")
        print(f"Confidence: {a['confidence']:.1f}%")
        print("Score Breakdown:")
        for component, score in a['score_breakdown'].items():
            print(f"  - {component}: {score}")
```

### Example 5: Batch Processing Multiple Projects

```python
from ai_assignee import AITaskAssigner

assigner = AITaskAssigner("sliit", "agilemind_db")

projects = [10237, 10204, 10270]  # Your project IDs

for project_id in projects:
    print(f"\nProcessing Project {project_id}...")
    assignments = assigner.run_assignment(project_id, save_to_db=True)
    print(f"✓ Assigned {len(assignments)} tasks")
```

## Running from Command Line

### Run AI Assignment
```bash
cd d:\Research\AgileMindTools\Assign_Tasks
python ai_assignee.py
```

### Run Comparison
```bash
cd d:\Research\AgileMindTools\Assign_Tasks
python compare_systems.py
```

### Run Old System (for reference)
```bash
cd d:\Research\AgileMindTools\Assign_Tasks
python assignee.py
```

## Understanding Output

### Assignment Output
```
Task ID              Assignee                            Confidence   Issue Type      Points   AI    
------------------------------------------------------------------------------------------------------------------------
TAM-48-1            lahiru@my.sliit.lk                  87.5%        feature         5        ✓     
  └─ Breakdown: Skill=45.0, History=38.5, Workload=18.0, AI-Sim=16.2, AI-Pred=14.8
```

**Interpreting the Breakdown:**
- **Skill**: How well developer's technologies match task requirements
- **History**: Developer's past performance on similar tasks
- **Workload**: Current workload balance (higher = less loaded)
- **AI-Sim**: TF-IDF cosine similarity score
- **AI-Pred**: Naive Bayes prediction probability

### Confidence Levels

| Confidence | Interpretation | Action |
|-----------|----------------|--------|
| 90-100% | Excellent match | Accept with high confidence |
| 70-89% | Good match | Accept, monitor performance |
| 50-69% | Moderate match | Review manually |
| Below 50% | Weak match | Consider manual assignment |

## Customization

### Adjust Scoring Weights

Edit `ai_assignee.py` to modify scoring weights:

```python
# In calculate_skill_match_score()
tech_score = min(40, tech_overlap * 10)  # Change multiplier for tech matching
stack_match_score = 20  # Change stack matching weight

# In calculate_history_match_score()
score += familiarity_ratio * 20  # Change issue type weight
score += tech_familiarity * 20   # Change technology familiarity weight
```

### Filter by Confidence Threshold

```python
# Only save high-confidence assignments
assignments = assigner.run_assignment(10237, save_to_db=False)
high_confidence = [a for a in assignments if a['confidence'] >= 70]

# Save only high-confidence assignments
for assignment in high_confidence:
    # Custom save logic
    pass
```

## Troubleshooting

### Issue: ModuleNotFoundError: No module named 'numpy'
**Solution:**
```bash
pip install numpy pandas
```

### Issue: No historical data, low confidence scores
**Solution:**
- Ensure you have completed tasks with assignees in the database
- The system needs at least 10-20 completed tasks for good training
- Check that `status` is 'done' or 'in_progress' for historical tasks

### Issue: All assignments have 0% confidence
**Solution:**
- Verify developer profiles have `user_data` with technologies and stack
- Check that tasks have proper tags and issue_type
- Ensure project_id matches between developers and tasks

### Issue: Database connection errors
**Solution:**
- Verify `.env` file exists and has correct credentials
- Check database server is running
- Ensure you have proper permissions on the database

## Best Practices

1. **Start with Dry Runs**: Always test with `save_to_db=False` first
2. **Review Low Confidence**: Manually review assignments below 70% confidence
3. **Monitor Performance**: Track actual task completion vs. assignments
4. **Update Profiles**: Keep developer profiles current with technologies
5. **Regular Training**: The system improves as more tasks are completed
6. **Compare Systems**: Use the comparison tool to validate AI decisions

## Integration with Existing Workflow

### Option 1: Replace Old System
```python
# In your existing code, replace:
# from assignee import assign_tasks_to_developers
# assignments = assign_tasks_to_developers(project_id, tenant, tenant_db)

# With:
from ai_assignee import AITaskAssigner
assigner = AITaskAssigner(tenant, tenant_db)
assignments = assigner.run_assignment(project_id, save_to_db=True)
```

### Option 2: Hybrid Approach
```python
from ai_assignee import AITaskAssigner

assigner = AITaskAssigner(tenant, tenant_db)
assignments = assigner.run_assignment(project_id, save_to_db=False)

# Use AI for high-confidence, fallback to manual for low-confidence
for assignment in assignments:
    if assignment['confidence'] >= 70:
        # Save AI assignment
        save_assignment(assignment)
    else:
        # Flag for manual review
        flag_for_review(assignment)
```

### Option 3: Gradual Rollout
```python
# Week 1: Compare only
comparator.run_comparison(project_id)

# Week 2: Use AI for 25% of tasks
if random.random() < 0.25:
    use_ai_assignment()
else:
    use_old_assignment()

# Week 3: Use AI for 50% of tasks
# Week 4: Use AI for 100% of tasks
```

## Performance Metrics to Track

1. **Assignment Accuracy**: % of assignments that don't require reassignment
2. **Task Completion Time**: Compare AI vs manual assignments
3. **Developer Satisfaction**: Survey developers on assignment quality
4. **Workload Balance**: Standard deviation of tasks per developer
5. **Confidence Calibration**: Do high-confidence assignments perform better?

## Next Steps

1. Run the comparison tool to see how AI differs from current assignments
2. Review the AI_ASSIGNMENT_README.md for detailed technical information
3. Start with a small project for testing
4. Gradually increase usage as confidence grows
5. Provide feedback to improve the system

## Support

For questions or issues:
1. Check the detailed README: `AI_ASSIGNMENT_README.md`
2. Review the comparison output for insights
3. Examine the score breakdown for specific assignments
4. Adjust scoring weights based on your team's needs
