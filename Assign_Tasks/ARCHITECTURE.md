# AI Task Assignment System - Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              INPUT DATA SOURCES                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────────┐  │
│  │   DEVELOPERS     │  │  UNASSIGNED      │  │   HISTORICAL                 │  │
│  │                  │  │  TASKS           │  │   ASSIGNMENTS                │  │
│  │ • Email          │  │                  │  │                              │  │
│  │ • Technologies   │  │ • Summary        │  │ • Completed Tasks            │  │
│  │ • Stack          │  │ • Description    │  │ • Assignees                  │  │
│  │ • Experience     │  │ • Tags           │  │ • Performance Data           │  │
│  │ • Projects       │  │ • Issue Type     │  │ • Story Points               │  │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────────────────┘  │
│           │                     │                      │                         │
└───────────┼─────────────────────┼──────────────────────┼─────────────────────────┘
            │                     │                      │
            └─────────────────────┼──────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         AI PROCESSING PIPELINE                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────┐    │
│  │  STEP 1: DEVELOPER PROFILE BUILDING                                    │    │
│  │  ─────────────────────────────────────────────────────────────────     │    │
│  │  • Extract technologies, stack, experience                             │    │
│  │  • Analyze historical task completion                                  │    │
│  │  • Calculate performance metrics                                       │    │
│  │  • Build technology usage patterns                                     │    │
│  └────────────────────────────────────────────────────────────────────────┘    │
│                                  │                                               │
│                                  ▼                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐    │
│  │  STEP 2: TF-IDF VECTORIZATION                                          │    │
│  │  ─────────────────────────────────────────────────────────────────     │    │
│  │  • Tokenize task descriptions and developer profiles                   │    │
│  │  • Calculate term frequency (TF)                                       │    │
│  │  • Calculate inverse document frequency (IDF)                          │    │
│  │  • Generate TF-IDF vectors for semantic matching                       │    │
│  └────────────────────────────────────────────────────────────────────────┘    │
│                                  │                                               │
│                                  ▼                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐    │
│  │  STEP 3: NAIVE BAYES TRAINING                                          │    │
│  │  ─────────────────────────────────────────────────────────────────     │    │
│  │  • Learn from historical task-developer pairs                          │    │
│  │  • Calculate class priors P(developer)                                 │    │
│  │  • Calculate feature probabilities P(feature|developer)                │    │
│  │  • Apply Laplace smoothing                                             │    │
│  └────────────────────────────────────────────────────────────────────────┘    │
│                                  │                                               │
│                                  ▼                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐    │
│  │  STEP 4: MULTI-FACTOR SCORING (for each task-developer pair)          │    │
│  │  ─────────────────────────────────────────────────────────────────     │    │
│  │                                                                         │    │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │    │
│  │  │ SKILL MATCH SCORE (0-70 points)                                 │  │    │
│  │  │ • Technology overlap: task tags ∩ developer technologies        │  │    │
│  │  │ • Stack matching: backend/frontend/fullstack alignment          │  │    │
│  │  │ • Experience bonus: years of experience                         │  │    │
│  │  └─────────────────────────────────────────────────────────────────┘  │    │
│  │                                                                         │    │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │    │
│  │  │ HISTORY MATCH SCORE (0-60 points)                               │  │    │
│  │  │ • Issue type familiarity: past work on similar types            │  │    │
│  │  │ • Technology familiarity: frequency of tech usage               │  │    │
│  │  │ • Completion efficiency: logged_hours / estimated_hours         │  │    │
│  │  │ • Priority handling: experience with task priority              │  │    │
│  │  └─────────────────────────────────────────────────────────────────┘  │    │
│  │                                                                         │    │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │    │
│  │  │ WORKLOAD BALANCE SCORE (0-20 points)                            │  │    │
│  │  │ • Current workload calculation                                  │  │    │
│  │  │ • Inverse scoring: less loaded = higher score                   │  │    │
│  │  │ • Fair distribution across team                                 │  │    │
│  │  └─────────────────────────────────────────────────────────────────┘  │    │
│  │                                                                         │    │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │    │
│  │  │ AI SIMILARITY SCORE (0-20 points)                               │  │    │
│  │  │ • Cosine similarity: cos(θ) = (A·B) / (||A|| ||B||)            │  │    │
│  │  │ • Semantic matching between task and developer vectors          │  │    │
│  │  │ • Captures implicit skill relationships                         │  │    │
│  │  └─────────────────────────────────────────────────────────────────┘  │    │
│  │                                                                         │    │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │    │
│  │  │ AI PREDICTION SCORE (0-20 points)                               │  │    │
│  │  │ • Naive Bayes probability: P(dev|task features)                 │  │    │
│  │  │ • Learns from successful historical assignments                 │  │    │
│  │  │ • Identifies hidden patterns in assignments                     │  │    │
│  │  └─────────────────────────────────────────────────────────────────┘  │    │
│  │                                                                         │    │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │    │
│  │  │ TOTAL SCORE = Σ(all component scores)                           │  │    │
│  │  │ CONFIDENCE = (total_score / max_possible_score) × 100%          │  │    │
│  │  └─────────────────────────────────────────────────────────────────┘  │    │
│  │                                                                         │    │
│  └────────────────────────────────────────────────────────────────────────┘    │
│                                  │                                               │
│                                  ▼                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐    │
│  │  STEP 5: ASSIGNMENT SELECTION                                          │    │
│  │  ─────────────────────────────────────────────────────────────────     │    │
│  │  • For each task, select developer with highest total score            │    │
│  │  • Update workload tracking                                            │    │
│  │  • Generate confidence percentage                                      │    │
│  │  • Create detailed score breakdown                                     │    │
│  └────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
└──────────────────────────────────────┬───────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                   OUTPUT                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────┐    │
│  │  TASK ASSIGNMENTS WITH METADATA                                        │    │
│  │  ─────────────────────────────────────────────────────────────────     │    │
│  │  {                                                                      │    │
│  │    "task_id": "TAM-48-1",                                              │    │
│  │    "assignee": "developer@example.com",                                │    │
│  │    "confidence": 87.5,                                                 │    │
│  │    "score_breakdown": {                                                │    │
│  │      "skill_match": 45.0,                                              │    │
│  │      "history_match": 38.5,                                            │    │
│  │      "workload_balance": 18.0,                                         │    │
│  │      "ai_similarity": 16.2,                                            │    │
│  │      "ai_prediction": 14.8,                                            │    │
│  │      "total": 132.5                                                    │    │
│  │    },                                                                  │    │
│  │    "ai_powered": true                                                  │    │
│  │  }                                                                      │    │
│  └────────────────────────────────────────────────────────────────────────┘    │
│                                  │                                               │
│                    ┌─────────────┴─────────────┐                                │
│                    │                           │                                 │
│                    ▼                           ▼                                 │
│  ┌──────────────────────────────┐  ┌──────────────────────────────┐            │
│  │   DATABASE UPDATE            │  │   PERFORMANCE TRACKING       │            │
│  │                              │  │                              │            │
│  │ • Update assignee field      │  │ • Log confidence scores      │            │
│  │ • Set updated_at timestamp   │  │ • Track assignment patterns  │            │
│  │ • Maintain audit trail       │  │ • Monitor accuracy metrics   │            │
│  └──────────────────────────────┘  └──────────────────────────────┘            │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────────┐
│                          CONFIDENCE INTERPRETATION                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  90-100%  ████████████████████  Excellent Match - Accept with high confidence   │
│  70-89%   ██████████████░░░░░░  Good Match - Accept, monitor performance        │
│  50-69%   ██████████░░░░░░░░░░  Moderate Match - Review manually                │
│  0-49%    ████░░░░░░░░░░░░░░░░  Weak Match - Consider manual assignment         │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────────┐
│                          KEY ADVANTAGES                                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ✓ Self-Learning: Improves accuracy as more tasks are completed                 │
│  ✓ Multi-Factor: Considers 5 different scoring components                       │
│  ✓ Transparent: Provides detailed score breakdown for each assignment           │
│  ✓ Balanced: Ensures fair workload distribution across team                     │
│  ✓ Semantic: Understands task-skill relationships beyond keywords               │
│  ✓ Adaptive: Learns from historical patterns and developer performance          │
│  ✓ Confident: Provides confidence metrics for decision support                  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Mathematical Formulas

### TF-IDF Calculation
```
TF(term, document) = count(term in document) / total_terms_in_document

IDF(term) = log((total_documents + 1) / (documents_containing_term + 1)) + 1

TF-IDF(term, document) = TF(term, document) × IDF(term)
```

### Cosine Similarity
```
similarity(A, B) = cos(θ) = (A · B) / (||A|| × ||B||)

where:
  A · B = Σ(Ai × Bi)  (dot product)
  ||A|| = √(Σ(Ai²))   (magnitude of A)
  ||B|| = √(Σ(Bi²))   (magnitude of B)
```

### Naive Bayes Probability
```
P(developer|task) ∝ P(developer) × Π P(feature_i|developer)

where:
  P(developer) = count(tasks assigned to developer) / total_tasks
  P(feature|developer) = (count(feature in developer's tasks) + 1) / (developer's total tasks + 2)
```

### Confidence Score
```
confidence = (total_score / max_possible_score) × 100%

where:
  max_possible_score = 150 (sum of all component maximums)
  total_score = skill_score + history_score + workload_score + similarity_score + prediction_score
```

## Data Flow Summary

1. **Input** → Developers, Tasks, Historical Data
2. **Processing** → Profile Building → Vectorization → ML Training → Scoring
3. **Selection** → Best Match Selection → Confidence Calculation
4. **Output** → Assignments + Metadata → Database + Tracking
