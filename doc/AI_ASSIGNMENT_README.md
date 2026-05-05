# AI-Powered Task Assignment System

## Overview

This AI-enhanced task assignment system uses **machine learning techniques** (without deep learning or LLMs) to intelligently assign tasks to developers based on their skills, experience, and historical performance.

## Key Features

### 1. **Multi-Factor Scoring System**
The system evaluates each developer-task pair using multiple scoring components:

- **Skill Match Score (0-70 points)**
  - Technology overlap between task tags and developer technologies
  - Stack matching (backend/frontend/fullstack)
  - Experience years bonus

- **History Match Score (0-60 points)**
  - Issue type familiarity
  - Technology familiarity from past work
  - Completion efficiency (how close to estimates)
  - Priority handling experience

- **Workload Balance Score (0-20 points)**
  - Prefers developers with lower current workload
  - Ensures fair distribution of tasks

- **AI Similarity Score (0-20 points)**
  - Uses TF-IDF vectorization and cosine similarity
  - Matches task descriptions to developer expertise

- **AI Prediction Score (0-20 points)**
  - Naive Bayes classifier trained on historical assignments
  - Learns patterns from past successful assignments

**Total Maximum Score: 150 points**

### 2. **Confidence Scoring**
Each assignment includes a confidence percentage (0-100%) indicating how well the developer matches the task requirements.

### 3. **Self-Learning System**
The AI learns from historical data:
- Analyzes completed tasks and their assignees
- Builds developer profiles based on past performance
- Adapts recommendations based on success patterns

## Machine Learning Techniques Used

### 1. **TF-IDF (Term Frequency-Inverse Document Frequency)**
- Converts task descriptions into numerical vectors
- Identifies important keywords in task requirements
- Enables semantic matching between tasks and developer expertise

### 2. **Cosine Similarity**
- Measures similarity between task requirements and developer skills
- Ranges from 0 (no similarity) to 1 (perfect match)
- Helps find developers whose expertise aligns with task needs

### 3. **Naive Bayes Classification**
- Probabilistic classifier that learns from historical assignments
- Predicts which developer is most likely to be assigned based on task features
- Uses Laplace smoothing to handle unseen features

### 4. **Feature Engineering**
Extracts and analyzes:
- Task summary and description
- Issue types (story, bug, feature, change)
- Technology tags
- Priority levels
- Story points and estimated hours

## How It Works

### Step 1: Data Collection
```python
# Fetch developers for the project
developers = ai_assigner.fetch_developers(project_id)

# Fetch unassigned tasks
tasks = ai_assigner.get_unassigned_tasks(project_id)

# Fetch historical assignments for training
historical_tasks, assignees = ai_assigner.fetch_historical_assignments(project_id)
```

### Step 2: Training Phase
```python
# Build developer profiles from historical data
ai_assigner.build_developer_profiles(developers, historical_tasks, assignees)

# Train TF-IDF vectorizer on task descriptions
ai_assigner.tfidf.fit(task_documents)

# Train Naive Bayes classifier on historical assignments
ai_assigner.nb_classifier.fit(task_vectors, assignees)
```

### Step 3: Assignment Phase
```python
for each task:
    for each developer:
        # Calculate component scores
        skill_score = calculate_skill_match_score(task, developer)
        history_score = calculate_history_match_score(task, developer)
        workload_score = calculate_workload_balance_score(developer)
        similarity_score = cosine_similarity(task_vector, dev_vector)
        nb_score = naive_bayes_predict_proba(task_vector, developer)
        
        # Total score
        total_score = sum(all_scores)
    
    # Assign to developer with highest score
    assign_task_to_best_developer()
```

### Step 4: Confidence Calculation
```python
confidence = (total_score / max_possible_score) * 100
```

## Usage

### Basic Usage
```python
from ai_assignee import AITaskAssigner

# Initialize
ai_assigner = AITaskAssigner(
    tenant_table="sliit",
    tenant_db="agilemind_db"
)

# Run assignment
assignments = ai_assigner.run_assignment(
    project_id=10237,
    save_to_db=True  # Set to False for dry-run
)

# View results
for assignment in assignments:
    print(f"Task: {assignment['task_id']}")
    print(f"Assignee: {assignment['assignee']}")
    print(f"Confidence: {assignment['confidence']}%")
    print(f"Score Breakdown: {assignment['score_breakdown']}")
```

### Advanced Usage - Custom Scoring Weights
You can modify the scoring weights in the code:

```python
# In calculate_skill_match_score()
tech_score = min(40, tech_overlap * 10)  # Adjust multiplier
stack_match_score = 20  # Adjust stack matching weight

# In calculate_history_match_score()
familiarity_ratio * 20  # Adjust issue type weight
tech_familiarity * 20   # Adjust technology familiarity weight
```

## Output Format

Each assignment includes:

```json
{
    "task_id": "TAM-123",
    "assignee": "developer@example.com",
    "summary": "Implement user authentication",
    "issue_type": "feature",
    "story_points": 5,
    "confidence": 87.5,
    "score_breakdown": {
        "skill_match": 45.0,
        "history_match": 38.5,
        "workload_balance": 18.0,
        "ai_similarity": 16.2,
        "ai_prediction": 14.8,
        "total": 132.5
    },
    "ai_powered": true
}
```

## Advantages Over Rule-Based System

| Feature | Old System | AI-Enhanced System |
|---------|-----------|-------------------|
| **Matching Accuracy** | Basic keyword matching | Multi-factor semantic matching |
| **Learning Capability** | Static rules | Learns from historical data |
| **Confidence Scoring** | No confidence metrics | Provides confidence percentage |
| **Workload Balancing** | Simple point counting | Intelligent load distribution |
| **Technology Matching** | Exact tag matching only | Semantic similarity + exact matching |
| **Historical Context** | Limited history usage | Comprehensive performance analysis |
| **Adaptability** | Manual rule updates needed | Self-adapting based on outcomes |

## Performance Metrics

The system tracks:
- **Average Confidence**: Mean confidence across all assignments
- **High Confidence Rate**: Percentage of assignments with ≥70% confidence
- **Training Data Size**: Number of historical assignments used
- **Developer Coverage**: Number of developers with historical data

## Fallback Mechanism

If insufficient historical data is available:
- System falls back to rule-based assignment
- Still uses skill matching and workload balancing
- Marks assignments as `ai_powered: false`

## Database Schema Requirements

### Required Tables

1. **Users Table** (e.g., `sliit`)
```sql
- email
- first_name
- last_name
- role
- status
- projects (JSON array)
- user_data (JSON with stack, technologies, experience_years)
```

2. **Project Backlog Table**
```sql
- id
- project_id
- summary
- description
- issue_type
- status
- priority
- assignee
- tags (JSON)
- story_points
- estimated_hours
- logged_hours
- parent_task_id
- updated_at
```

3. **Project Backlog Priority Table**
```sql
- backlog_id
- project_id
- sprint_id
- rank
```

## Configuration

### Environment Variables
```python
TENANT_TABLE = "sliit"          # Your tenant table name
TENANT_DB = "agilemind_db"      # Your database name
PROJECT_ID = 10237              # Project to assign tasks for
```

## Troubleshooting

### Issue: Low Confidence Scores
**Solution**: 
- Ensure developers have complete profiles (technologies, stack, experience)
- Add more historical assignment data
- Verify task tags are properly set

### Issue: No Assignments Generated
**Solution**:
- Check if developers exist for the project
- Verify unassigned tasks are available
- Check database connectivity

### Issue: AI Not Training
**Solution**:
- Ensure historical assignments exist (status: done/in_progress)
- Verify assignee field is populated in historical data
- Check minimum data threshold (need at least a few completed tasks)

## Future Enhancements

Potential improvements:
1. **Time-based Learning**: Weight recent assignments more heavily
2. **Feedback Loop**: Learn from reassignments and task completions
3. **Team Dynamics**: Consider developer collaboration patterns
4. **Skill Gap Analysis**: Identify training needs based on assignment patterns
5. **Sprint Planning Integration**: Optimize assignments across sprint boundaries
6. **Real-time Adaptation**: Update models as new tasks are completed

## Comparison with Original System

### Original `assignee.py`
- Simple scoring: Technology match (10 pts) + Stack match (5 pts) + Experience
- No historical learning
- No confidence metrics
- Basic workload balancing

### New `ai_assignee.py`
- Advanced scoring: 5 different components totaling 150 points
- Machine learning from historical data
- Confidence percentages for each assignment
- Intelligent workload distribution
- Semantic similarity matching
- Probabilistic predictions

## Example Output

```
====================================================================================================
AI-POWERED TASK ASSIGNMENT SYSTEM
====================================================================================================

✓ Successfully assigned 15 tasks

Task ID              Assignee                            Confidence   Issue Type      Points   AI    
------------------------------------------------------------------------------------------------------------------------
TAM-48-1            lahiru@my.sliit.lk                  87.5%        feature         5        ✓     
  └─ Breakdown: Skill=45.0, History=38.5, Workload=18.0, AI-Sim=16.2, AI-Pred=14.8
TAM-48-2            beweerapperuma@gmail.com            82.3%        bug             3        ✓     
  └─ Breakdown: Skill=40.0, History=35.0, Workload=19.5, AI-Sim=15.8, AI-Pred=13.0
TAM-48-3            lahiru@my.sliit.lk                  79.1%        story           8        ✓     
  └─ Breakdown: Skill=42.0, History=32.5, Workload=17.0, AI-Sim=14.6, AI-Pred=12.0

====================================================================================================
Statistics:
  - Average Confidence: 83.2%
  - High Confidence Assignments (≥70%): 14/15
  - AI-Powered: Yes
====================================================================================================
```

## License

This AI assignment system is part of the AgileMind Tools project.

## Support

For issues or questions, please refer to the main project documentation or contact the development team.
