# Flexible Stack Detection System - No More Hard-Coded Keywords! 🎉

## Problem Solved

### ❌ Old System (Hard-Coded)
```python
# BRITTLE - Breaks when keywords change
if 'backend' in task_type or 'api' in task_type or 'database' in task_type:
    if 'backend' in dev_stack:
        score += 20
elif 'frontend' in task_type or 'ui' in task_type or 'ux' in task_type:
    if 'frontend' in dev_stack:
        score += 20
```

**Problems:**
- ❌ Hard-coded keywords
- ❌ Can't detect "microservice", "mobile", "devops"
- ❌ System breaks if naming changes
- ❌ Requires code changes to add new stacks
- ❌ No flexibility

### ✅ New System (Configurable & Flexible)
```python
# FLEXIBLE - Easy to update, no code changes needed
STACK_KEYWORDS = {
    'backend': ['backend', 'api', 'database', 'microservice', 'service', ...],
    'frontend': ['frontend', 'ui', 'ux', 'react', 'angular', ...],
    'mobile': ['mobile', 'android', 'ios', 'flutter', ...],
    'devops': ['devops', 'docker', 'kubernetes', ...],
    'data': ['data', 'ml', 'ai', 'analytics', ...],
    'testing': ['testing', 'qa', 'automation', ...]
}

detected_stacks = self.detect_stack_from_tags(task_tags, issue_type)
score = self.calculate_stack_match_score(detected_stacks, dev_stack)
```

**Benefits:**
- ✅ Tag-based detection
- ✅ Supports 6 stack types (backend, frontend, mobile, devops, data, testing)
- ✅ Easy to add new keywords - just update the dictionary
- ✅ Can be moved to config file or database
- ✅ Intelligent matching with partial scores

## How It Works

### 1. Stack Detection (`detect_stack_from_tags`)

```python
def detect_stack_from_tags(self, tags: List[str], issue_type: str = '') -> List[str]:
    """
    Detect which stacks are relevant based on tags and issue type.
    """
    detected_stacks = set()
    
    # Combine tags and issue_type for detection
    all_keywords = [tag.lower() for tag in tags] + [issue_type.lower()]
    
    # Check each stack's keywords
    for stack, keywords in self.STACK_KEYWORDS.items():
        for keyword in all_keywords:
            if any(stack_keyword in keyword for stack_keyword in keywords):
                detected_stacks.add(stack)
                break
    
    return list(detected_stacks)
```

**Example:**
```python
tags = ['react', 'node', 'docker']
issue_type = 'feature'

detected_stacks = detect_stack_from_tags(tags, issue_type)
# Result: ['frontend', 'backend', 'devops']
```

### 2. Stack Matching Score (`calculate_stack_match_score`)

```python
def calculate_stack_match_score(self, detected_stacks: List[str], dev_stack: List[str]) -> float:
    """
    Calculate stack matching score (0-20 points).
    Awards partial points for partial matches.
    """
    if not detected_stacks:
        return 0.0
    
    # Calculate match ratio
    matches = sum(1 for stack in detected_stacks if stack in dev_stack_lower)
    match_ratio = matches / len(detected_stacks)
    
    # Award points based on match ratio
    score = match_ratio * 20
    
    # Bonus for fullstack developers when multiple stacks needed
    if len(detected_stacks) >= 2 and 'backend' in dev_stack and 'frontend' in dev_stack:
        score = min(20, score + 5)
    
    return score
```

**Example:**
```python
detected_stacks = ['backend', 'frontend', 'devops']
dev_stack = ['backend', 'frontend']

score = calculate_stack_match_score(detected_stacks, dev_stack)
# Match: 2/3 = 66.7%
# Score: 0.667 * 20 = 13.3 points
# Bonus: +5 for fullstack = 18.3 points
```

## Supported Stack Types

### 1. Backend
```python
'backend': [
    'backend', 'api', 'database', 'server', 'microservice', 
    'service', 'rest', 'graphql', 'sql', 'nosql', 'redis',
    'kafka', 'rabbitmq', 'mongodb', 'postgresql', 'mysql',
    'node', 'express', 'django', 'flask', 'spring', 'fastapi'
]
```

### 2. Frontend
```python
'frontend': [
    'frontend', 'ui', 'ux', 'web', 'react', 'angular', 'vue',
    'svelte', 'nextjs', 'nuxt', 'html', 'css', 'javascript',
    'typescript', 'tailwind', 'bootstrap', 'material-ui',
    'responsive', 'mobile-web', 'pwa'
]
```

### 3. Mobile
```python
'mobile': [
    'mobile', 'android', 'ios', 'react-native', 'flutter',
    'swift', 'kotlin', 'xamarin', 'ionic', 'cordova',
    'mobile-app', 'app-development'
]
```

### 4. DevOps
```python
'devops': [
    'devops', 'ci/cd', 'docker', 'kubernetes', 'jenkins',
    'github-actions', 'gitlab-ci', 'aws', 'azure', 'gcp',
    'terraform', 'ansible', 'deployment', 'infrastructure'
]
```

### 5. Data/ML
```python
'data': [
    'data', 'analytics', 'ml', 'ai', 'machine-learning',
    'data-science', 'etl', 'pipeline', 'spark', 'hadoop',
    'pandas', 'numpy', 'tensorflow', 'pytorch'
]
```

### 6. Testing/QA
```python
'testing': [
    'testing', 'qa', 'test', 'unit-test', 'integration-test',
    'e2e', 'selenium', 'jest', 'pytest', 'cypress', 'automation'
]
```

## Usage Examples

### Example 1: Backend Microservice
```python
task = {
    'tags': ['node', 'microservice', 'mongodb'],
    'issue_type': 'feature'
}

# Detection
detected_stacks = ['backend']

# Developer with backend stack
dev_stack = ['backend']
score = 20  # Perfect match!
```

### Example 2: Mobile App
```python
task = {
    'tags': ['react-native', 'ios', 'android'],
    'issue_type': 'mobile-app'
}

# Detection
detected_stacks = ['mobile', 'frontend']

# Developer with mobile stack
dev_stack = ['mobile']
score = 10  # 1/2 match = 50% = 10 points
```

### Example 3: Full-Stack Feature
```python
task = {
    'tags': ['react', 'node', 'postgresql'],
    'issue_type': 'feature'
}

# Detection
detected_stacks = ['frontend', 'backend']

# Fullstack developer
dev_stack = ['frontend', 'backend']
score = 20 + 5 = 25 → capped at 20  # Perfect match + fullstack bonus
```

### Example 4: DevOps Task
```python
task = {
    'tags': ['docker', 'kubernetes', 'ci/cd'],
    'issue_type': 'deployment'
}

# Detection
detected_stacks = ['devops']

# Backend developer (no devops)
dev_stack = ['backend']
score = 0  # No match
```

## How to Add New Keywords

### Option 1: Update the Dictionary (Quick)
```python
# In ai_assignee.py, line ~170
STACK_KEYWORDS = {
    'backend': [
        'backend', 'api', 'database',
        'your-new-keyword-here'  # ← Add here
    ],
    # ... other stacks
}
```

### Option 2: Move to Config File (Recommended)
```python
# config/stack_keywords.json
{
    "backend": ["backend", "api", "database", "microservice"],
    "frontend": ["frontend", "ui", "react", "angular"],
    "mobile": ["mobile", "android", "ios", "flutter"],
    "custom_stack": ["your", "custom", "keywords"]
}

# Load in ai_assignee.py
import json

with open('config/stack_keywords.json') as f:
    STACK_KEYWORDS = json.load(f)
```

### Option 3: Store in Database (Enterprise)
```sql
CREATE TABLE stack_keywords (
    id INT PRIMARY KEY AUTO_INCREMENT,
    stack VARCHAR(50),
    keyword VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO stack_keywords (stack, keyword) VALUES
('backend', 'backend'),
('backend', 'api'),
('backend', 'microservice'),
('frontend', 'react'),
('mobile', 'flutter');
```

```python
# Load from database
def load_stack_keywords_from_db(self):
    query = "SELECT stack, keyword FROM stack_keywords"
    df = read_from_mysql_with_params(query, {}, self.tenant_db)
    
    keywords = {}
    for _, row in df.iterrows():
        if row['stack'] not in keywords:
            keywords[row['stack']] = []
        keywords[row['stack']].append(row['keyword'])
    
    return keywords
```

## Advantages Over Hard-Coded System

| Feature | Hard-Coded | Flexible System |
|---------|-----------|-----------------|
| **Add New Stack** | Code change required | Just add to dictionary |
| **Add New Keyword** | Code change required | Just add to list |
| **Support Mobile** | ❌ Not supported | ✅ Fully supported |
| **Support DevOps** | ❌ Not supported | ✅ Fully supported |
| **Support Data/ML** | ❌ Not supported | ✅ Fully supported |
| **Partial Matching** | ❌ All or nothing | ✅ Proportional scoring |
| **Fullstack Bonus** | ❌ Not available | ✅ +5 points for versatility |
| **Config File** | ❌ Not possible | ✅ Easy to implement |
| **Database Storage** | ❌ Not possible | ✅ Easy to implement |
| **Maintainability** | 🔴 Low | 🟢 High |

## Migration Path

### Phase 1: Current (In Code)
```python
# Keywords defined in class
STACK_KEYWORDS = { ... }
```

### Phase 2: Config File
```python
# Move to config/stack_keywords.json
with open('config/stack_keywords.json') as f:
    STACK_KEYWORDS = json.load(f)
```

### Phase 3: Database
```python
# Load from database on initialization
def __init__(self, tenant_table, tenant_db):
    self.STACK_KEYWORDS = self.load_stack_keywords_from_db()
```

### Phase 4: Admin UI
```
Admin Panel → Stack Management → Add/Edit Keywords
```

## Testing

```python
# Test detection
def test_stack_detection():
    assigner = AITaskAssigner("sliit", "agilemind_db")
    
    # Test backend detection
    stacks = assigner.detect_stack_from_tags(['node', 'api'], 'feature')
    assert 'backend' in stacks
    
    # Test mobile detection
    stacks = assigner.detect_stack_from_tags(['flutter', 'ios'], 'mobile-app')
    assert 'mobile' in stacks
    
    # Test multiple stacks
    stacks = assigner.detect_stack_from_tags(['react', 'node', 'docker'], 'feature')
    assert set(stacks) == {'frontend', 'backend', 'devops'}
```

## Summary

✅ **No more hard-coded keywords!**  
✅ **Supports 6 stack types** (backend, frontend, mobile, devops, data, testing)  
✅ **Easy to extend** - just add to the dictionary  
✅ **Intelligent scoring** - partial matches get partial points  
✅ **Fullstack bonus** - rewards versatile developers  
✅ **Future-proof** - can move to config file or database  

The system is now **flexible, maintainable, and scalable**! 🚀

---

**Updated**: 2026-02-08  
**Version**: 2.0  
**Status**: Production Ready
