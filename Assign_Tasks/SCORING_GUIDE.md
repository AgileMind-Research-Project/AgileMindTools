# AI Task Assignment - Scoring Visualization

## Score Component Breakdown

```
MAXIMUM POSSIBLE SCORE: 150 POINTS
═══════════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────────────┐
│  SKILL MATCH SCORE (0-70 points) - 46.7% of total                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  Technology Overlap (0-40 points)                            │      │
│  │  ────────────────────────────────────────────────────────    │      │
│  │  • Each matching technology: +10 points                      │      │
│  │  • Example: Task tags [react, node, mysql]                   │      │
│  │            Developer techs [react, angular, node]            │      │
│  │            Match: react, node = 20 points                    │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  Stack Matching (0-20 points)                                │      │
│  │  ────────────────────────────────────────────────────────    │      │
│  │  • Backend task + Backend developer: +20 points              │      │
│  │  • Frontend task + Frontend developer: +20 points            │      │
│  │  • Fullstack task + Both stacks: +20 points                  │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  Experience Bonus (0-10 points)                              │      │
│  │  ────────────────────────────────────────────────────────    │      │
│  │  • Years of experience × 2 (capped at 10)                    │      │
│  │  • Example: 3 years = 6 points, 5+ years = 10 points         │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  HISTORY MATCH SCORE (0-60 points) - 40% of total                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  Issue Type Familiarity (0-20 points)                        │      │
│  │  ────────────────────────────────────────────────────────    │      │
│  │  • Ratio of past work on this issue type × 20               │      │
│  │  • Example: 15 bugs out of 30 tasks = 0.5 × 20 = 10 pts     │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  Technology Familiarity (0-20 points)                        │      │
│  │  ────────────────────────────────────────────────────────    │      │
│  │  • Frequency of using task technologies in past work         │      │
│  │  • Example: Used React in 20 of 30 tasks = 0.67 × 20 = 13   │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  Completion Efficiency (0-15 points)                         │      │
│  │  ────────────────────────────────────────────────────────    │      │
│  │  • Ratio: logged_hours / estimated_hours                     │      │
│  │  • 0.8-1.2 (within 20%): 15 points                          │      │
│  │  • 0.6-1.4 (within 40%): 10 points                          │      │
│  │  • Other: 5 points                                           │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  Priority Handling (0-5 points)                              │      │
│  │  ────────────────────────────────────────────────────────    │      │
│  │  • Has handled this priority level before: +5 points         │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  WORKLOAD BALANCE SCORE (0-20 points) - 13.3% of total                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  Current Workload Calculation                                │      │
│  │  ────────────────────────────────────────────────────────    │      │
│  │  • Inverse scoring: less loaded = higher score               │      │
│  │  • Formula: 20 × (1 - dev_workload/max_workload)            │      │
│  │  • Example:                                                   │      │
│  │    - Dev A: 10 points, Dev B: 20 points, Dev C: 5 points    │      │
│  │    - Max workload: 20                                        │      │
│  │    - Dev A score: 20 × (1 - 10/20) = 10 points              │      │
│  │    - Dev B score: 20 × (1 - 20/20) = 0 points               │      │
│  │    - Dev C score: 20 × (1 - 5/20) = 15 points               │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  AI SIMILARITY SCORE (0-20 points) - 13.3% of total                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  TF-IDF Cosine Similarity                                    │      │
│  │  ────────────────────────────────────────────────────────    │      │
│  │  • Semantic matching between task and developer              │      │
│  │  • Formula: similarity × 20                                  │      │
│  │  • Process:                                                   │      │
│  │    1. Convert task description to TF-IDF vector             │      │
│  │    2. Convert developer profile to TF-IDF vector            │      │
│  │    3. Calculate cosine similarity (0-1)                     │      │
│  │    4. Multiply by 20 for score                              │      │
│  │  • Example:                                                   │      │
│  │    - Similarity: 0.75                                        │      │
│  │    - Score: 0.75 × 20 = 15 points                           │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  AI PREDICTION SCORE (0-20 points) - 13.3% of total                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  Naive Bayes Probability                                     │      │
│  │  ────────────────────────────────────────────────────────    │      │
│  │  • Learned from historical assignments                       │      │
│  │  • Formula: P(developer|task) × 20                          │      │
│  │  • Process:                                                   │      │
│  │    1. Train on historical task-developer pairs              │      │
│  │    2. Calculate P(developer|task features)                  │      │
│  │    3. Multiply probability by 20 for score                  │      │
│  │  • Example:                                                   │      │
│  │    - Probability: 0.65                                       │      │
│  │    - Score: 0.65 × 20 = 13 points                           │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Example Calculation

```
TASK: "Implement user authentication with JWT tokens"
Tags: [backend, node, jwt, security]
Issue Type: feature
Priority: high
Story Points: 8

DEVELOPER: lahiru@my.sliit.lk
Technologies: [react, angular, node, python, mysql, java]
Stack: [backend, frontend]
Experience: 3 years
Past Tasks: 45 total (20 features, 15 bugs, 10 stories)
Past Technologies: node (25 times), react (30 times), mysql (20 times)

SCORING BREAKDOWN:
═══════════════════════════════════════════════════════════════════

1. SKILL MATCH SCORE
   ─────────────────
   • Technology Overlap:
     - Task: [backend, node, jwt, security]
     - Developer: [react, angular, node, python, mysql, java]
     - Matches: node
     - Score: 1 × 10 = 10 points
   
   • Stack Matching:
     - Task type: backend feature
     - Developer stack: [backend, frontend]
     - Match: backend
     - Score: 20 points
   
   • Experience Bonus:
     - 3 years × 2 = 6 points
   
   SUBTOTAL: 10 + 20 + 6 = 36 points

2. HISTORY MATCH SCORE
   ───────────────────
   • Issue Type Familiarity:
     - Past features: 20 out of 45 tasks
     - Ratio: 20/45 = 0.44
     - Score: 0.44 × 20 = 8.8 points
   
   • Technology Familiarity:
     - Node usage: 25 out of 45 tasks
     - Ratio: 25/45 = 0.56
     - Score: 0.56 × 20 = 11.2 points
   
   • Completion Efficiency:
     - Average ratio: 1.05 (within 20% of estimates)
     - Score: 15 points
   
   • Priority Handling:
     - Has handled high priority: Yes
     - Score: 5 points
   
   SUBTOTAL: 8.8 + 11.2 + 15 + 5 = 40 points

3. WORKLOAD BALANCE SCORE
   ──────────────────────
   • Current workload: 15 story points
   • Max workload in team: 25 story points
   • Ratio: 15/25 = 0.6
   • Score: 20 × (1 - 0.6) = 8 points
   
   SUBTOTAL: 8 points

4. AI SIMILARITY SCORE
   ───────────────────
   • Task vector: [0.3, 0.5, 0.2, 0.4, ...]
   • Developer vector: [0.2, 0.6, 0.1, 0.3, ...]
   • Cosine similarity: 0.78
   • Score: 0.78 × 20 = 15.6 points
   
   SUBTOTAL: 15.6 points

5. AI PREDICTION SCORE
   ───────────────────
   • Naive Bayes P(lahiru|task): 0.72
   • Score: 0.72 × 20 = 14.4 points
   
   SUBTOTAL: 14.4 points

TOTAL SCORE: 36 + 40 + 8 + 15.6 + 14.4 = 114 points
CONFIDENCE: (114 / 150) × 100 = 76%

RESULT: ✓ GOOD MATCH - Assign with confidence
```

## Visual Score Distribution

```
Component Contribution to Total Score:
═══════════════════════════════════════════════════════════════════

Skill Match (36/70)         ████████████████████░░░░░░░░░░  51.4%
History Match (40/60)       █████████████████████████████░  66.7%
Workload Balance (8/20)     ████████░░░░░░░░░░░░░░░░░░░░░░  40.0%
AI Similarity (15.6/20)     ███████████████████████████░░░  78.0%
AI Prediction (14.4/20)     █████████████████████████░░░░░  72.0%

Overall Score: 114/150      ████████████████████████░░░░░░  76.0%
```

## Confidence Level Interpretation

```
┌─────────────────────────────────────────────────────────────────┐
│  CONFIDENCE: 76% - GOOD MATCH                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ✓ This is a solid assignment with good confidence              │
│  ✓ Developer has relevant experience and skills                 │
│  ✓ Historical performance supports this assignment              │
│  ✓ AI models agree this is a good match                         │
│  ✓ Workload is reasonable                                       │
│                                                                  │
│  RECOMMENDATION: Accept this assignment                         │
│  MONITORING: Track completion time and quality                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Score Optimization Tips

### To Improve Skill Match Score:
- Ensure developer profiles have complete technology lists
- Add relevant tags to tasks
- Keep stack information up to date

### To Improve History Match Score:
- Complete more tasks to build history
- Log actual hours for better efficiency tracking
- Maintain consistent assignee information

### To Improve Workload Balance Score:
- Distribute tasks evenly across team
- Consider story points when assigning
- Monitor current workload regularly

### To Improve AI Scores:
- Provide detailed task descriptions
- Maintain rich historical data
- Ensure consistent data quality
- Allow system to learn from more completed tasks

## Comparison: Rule-Based vs AI Scoring

```
RULE-BASED SYSTEM (Old):
═══════════════════════════════════════════════════════════════════
Technology Match:     10 points per match
Stack Match:          5 points
Experience:           1-5 points
Work History Bonus:   3 points
Workload Penalty:     -0.5 per story point

TOTAL POSSIBLE: ~50-60 points (no upper limit)
CONFIDENCE: Not provided


AI-ENHANCED SYSTEM (New):
═══════════════════════════════════════════════════════════════════
Skill Match:          0-70 points (structured)
History Match:        0-60 points (comprehensive)
Workload Balance:     0-20 points (fair distribution)
AI Similarity:        0-20 points (semantic matching)
AI Prediction:        0-20 points (learned patterns)

TOTAL POSSIBLE: 150 points (normalized)
CONFIDENCE: 0-100% (transparent)
```

## Key Advantages

1. **Structured Scoring**: Clear maximum for each component
2. **Normalized Scale**: All scores on same 0-150 scale
3. **Transparent Confidence**: Easy to interpret percentage
4. **Multi-Dimensional**: Considers 5 different aspects
5. **Self-Learning**: AI components improve over time
6. **Balanced Approach**: Combines rules and machine learning
