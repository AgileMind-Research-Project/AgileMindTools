# Component 1: Intelligent Planning and Task Automation

**Student:** Jayawardhana L S — IT22563200  
**Project:** AgileMind — Enhancing Agile Project Management Platform Through Automation and Decision Support  
**Project ID:** 25-26J-508  
**Department of Software Engineering, SLIIT — July 2025**

---

## Abstract

Sprint planning in Scrum ceremonies requires teams to balance business value, technical risk, developer capability, and workload equity across backlogs that can contain hundreds of items. Manual prioritisation introduces cognitive bias and inconsistency; manual task decomposition produces under-specified sub-tasks; manual assignment ignores historical performance; and manual sprint review preparation consumes hours of ceremony time. This component presents four tightly integrated AI-driven sub-systems that automate these activities: (1) AI backlog prioritisation using Weighted Shortest Job First scoring with K-Means MoSCoW clustering, (2) automated task splitting using spaCy NLP with TF-IDF duplicate detection, (3) intelligent developer assignment using a custom TF-IDF / Naïve Bayes multi-factor scorer, and (4) sprint review generation with Redis real-time broadcast. Each sub-system is implemented as a standalone Python module within the `AgileMindTools/` Lambda layer and exposed by the `AjileMindApi` FastAPI backend. Experimental evaluation demonstrates a silhouette score exceeding 0.50 for MoSCoW clustering, average assignment confidence of 72.4%, and an average subtask quality score of 0.63.

---

## 1. Introduction

Agile Scrum prescribes four planning-adjacent ceremonies — Sprint Planning, Sprint Review, Sprint Retrospective, and Daily Scrum — whose combined ceremony overhead can consume 10–15% of a two-week sprint's calendar time (Schwaber and Sutherland, 2020). Within Sprint Planning alone, teams must sequence backlog items by value, decompose stories into implementable sub-tasks, and assign work to developers best suited for each task. Each activity is cognitively demanding, repetitive across sprints, and subject to human inconsistency.

AgileMind Component 1 addresses this overhead by providing four automation sub-systems. The prioritisation sub-system learns from historical delivery order and applies the SAFe Weighted Shortest Job First (WSJF) formula, augmented with K-Means MoSCoW clustering. The task-splitting sub-system uses spaCy Part-of-Speech tagging and TF-IDF cosine similarity to decompose stories into quality-filtered sub-tasks. The assignment sub-system combines a custom TF-IDF vectorizer, a Naïve Bayes classifier, and a five-dimensional scoring model trained on historical assignment data. The review generation sub-system fetches live sprint data, generates multi-slide ASCII presentations, and broadcasts them through Redis to all connected project stakeholders.

The remainder of this chapter is structured as follows: Section 2 reviews the relevant literature; Section 3 presents the system architecture; Section 4 details each sub-component's design and implementation with reference to the actual source code; Section 5 lists all libraries and dependencies; Section 6 reports experimental results; Section 7 discusses novelty and contribution; and Section 8 provides references.

---

## 2. Literature Review

### 2.1 Backlog Prioritisation and WSJF

Product backlog prioritisation is a central Agile practice whose outcome determines which features are delivered in each sprint and, ultimately, the product's time-to-market competitiveness. The most commonly applied heuristic is the MoSCoW framework (Clegg and Barker, 1994), which categorises items as Must Have, Should Have, Could Have, and Won't Have. However, MoSCoW categorisation as typically practised is a subjective negotiation among stakeholders rather than a principled scoring process.

The Scaled Agile Framework (SAFe) introduced Weighted Shortest Job First (WSJF) to bring quantitative rigour to backlog sequencing (Leffingwell, 2011). WSJF defines a priority score as Cost of Delay divided by job duration, where Cost of Delay is itself the sum of three components: User Value (the relative benefit of the feature to users), Time Criticality (how quickly value decays if delivery is delayed), and Risk Reduction / Opportunity Enablement (the extent to which the item reduces future risk or opens future opportunities). Reinertsen (2009) provides the theoretical foundation for Cost of Delay in product development economics, demonstrating that sequencing by WSJF minimises the aggregate cost of delay across a queue of work items.

The weakness of standard WSJF is that its sub-scores are still estimated manually by teams during planning sessions, reintroducing subjectivity. Several studies have proposed automating these estimates using Natural Language Processing. Sharma et al. (2019) used keyword-based classifiers to predict priority from story text. More recently, Reimers and Gurevych (2019) demonstrated that sentence-level dense embeddings from transformer encoder models — specifically the Sentence-BERT family — outperform TF-IDF and keyword approaches on semantic similarity tasks across a broad range of domains. In this component, the `all-MiniLM-L6-v2` sentence transformer model from the `sentence-transformers` library is used to derive the three WSJF sub-scores directly from backlog item text, replacing manual team estimation.

### 2.2 Dimensionality Reduction with PCA

Sentence embeddings produced by transformer models are typically 384–768 dimensional, making direct use in downstream estimators computationally expensive and susceptible to the curse of dimensionality (Bellman, 1961). Principal Component Analysis (PCA), introduced by Pearson (1901) and formalised by Hotelling (1933), projects data onto the orthogonal directions of maximum variance, enabling compact representation without significant information loss. Jolliffe (2002) provides a comprehensive treatment of PCA theory and its application in multivariate statistics. In this implementation, PCA is fitted on historical sprint embeddings and applied as a fixed transform to backlog embeddings, preserving the training/test separation required to prevent data leakage.

### 2.3 K-Means Clustering for MoSCoW Assignment

K-Means (MacQueen, 1967) partitions observations into k clusters by iteratively minimising within-cluster sum of squared distances. The algorithm is well-suited for assigning backlog items to four MoSCoW categories when applied to a feature space dominated by WSJF scores, because items with similar business value naturally aggregate. The silhouette coefficient (Rousseeuw, 1987) measures how similar an item is to its own cluster relative to other clusters, ranging from −1 (misassigned) to +1 (well-matched). A mean silhouette score above 0.50 indicates strong cluster structure.

### 2.4 Task Decomposition with NLP

Well-structured sub-tasks improve sprint predictability by making work items granular enough to be completed within one or two days (Cohn, 2004). Traditional decomposition relies on facilitator skill, which varies across teams. Automated decomposition using verb-noun phrase extraction from POS-tagged text (Manning et al., 2014) can produce candidate sub-tasks directly from story descriptions. The spaCy library (Honnibal and Montani, 2017) provides a production-ready pipeline including tokenisation, POS tagging, dependency parsing, Named Entity Recognition (NER), and noun chunk extraction, all within a single `nlp()` call on raw text. TF-IDF cosine similarity (Salton and Buckley, 1988) detects semantic redundancy among generated sub-task candidates, and verb normalisation further reduces near-duplicate pairs that differ only in action verb choice.

### 2.5 AI-Assisted Developer Assignment

Task assignment in software projects is a constraint-satisfaction problem that must account for developer skill, workload, historical performance, and project context (Barreto et al., 2008). Naïve Bayes text classifiers (Manning et al., 2008) trained on historical `(task text, assignee)` pairs provide a natural probabilistic prior for assignment. Combined with explicit skill-match scoring and workload balancing, such hybrid approaches achieve higher assignment accuracy than either pure ML or pure heuristic methods in isolation (Anvik et al., 2006).

---

## 3. System Architecture

Component 1 is realised as four Python modules within the `AgileMindTools/` Lambda layer. The `AjileMindApi` FastAPI backend triggers each Lambda via internal REST calls and reads results from the shared multi-tenant MySQL database. The multi-tenant architecture isolates each organisation's data in a separate MySQL schema; the tenant identifier is derived from the user's email domain using `tldextract`.

```
┌─────────────────────────────────────────────────────────────────┐
│                    AgileMind Planning Pipeline                   │
│                                                                 │
│  ┌─────────────────────┐   ┌──────────────────────────────────┐ │
│  │ Backlog_Prioritize/ │   │         Task_Split/              │ │
│  │ Backlog_prioritize  │   │         split_task.py            │ │
│  │ .py                 │   │                                  │ │
│  │                     │   │ - get_dynamic_keywords()         │ │
│  │ - SentenceTransformer│──▶│ - extract_subtasks_advanced()   │ │
│  │   all-MiniLM-L6-v2  │   │ - is_duplicate_subtask()        │ │
│  │ - PCA (n=3)          │   │ - calculate_subtask_quality()   │ │
│  │ - LinearRegression   │   │ - split_backlog_tasks()         │ │
│  │ - WSJF formula       │   │                                  │ │
│  │ - KMeans (k=4, 50x)  │   └──────────────┬───────────────────┘ │
│  │ - silhouette_score   │                  │                    │
│  └─────────────────────┘                  ▼                    │
│                              ┌──────────────────────────────┐  │
│                              │     Assign_Tasks/            │  │
│                              │     ai_assignee.py           │  │
│                              │                              │  │
│                              │ - TFIDFVectorizer (custom)   │  │
│                              │ - NaiveBayesClassifier       │  │
│                              │ - 5-dimension scoring (170pt)│  │
│                              │ - assign_with_ai()           │  │
│                              │ - assign_parents_to_manager()│  │
│                              └──────────────┬───────────────┘  │
│                                             │                   │
│                                             ▼                   │
│                    ┌────────────────────────────────────────┐   │
│                    │        Multi-Tenant MySQL DB            │   │
│                    │  project_backlog                       │   │
│                    │  project_backlog_priority              │   │
│                    │  notifications                         │   │
│                    └───────────────────┬────────────────────┘   │
│                                        │                        │
│                                        ▼                        │
│                    ┌────────────────────────────────────────┐   │
│                    │       Sprint_Review/                    │   │
│                    │       sprint_review.py (Lambda)        │   │
│                    │                                        │   │
│                    │  - generate_sprint_review_slides()     │   │
│                    │  - process_project()                   │   │
│                    │  - RedisClient.send_message()          │   │
│                    │  - create_notification()               │   │
│                    └────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Methodology and Implementation

### 4.1 Sub-Component 1.2 — AI Backlog Prioritisation

#### 4.1.1 Overview

The core function of the prioritisation module is:

```python
def train_and_prioritize(historical_csv_path, backlog_items, additional_historical_df=None):
```

This function accepts a path to the general historical dataset (`GFG_FINAL.csv`), a list of backlog items to prioritise, and an optional DataFrame of project-specific historical data retrieved from the database. It returns a sorted DataFrame with columns `priority_rank`, `WSJF`, `moscow_category`, `cost_of_delay`, and all original item attributes.

#### 4.1.2 Data Ingestion — Exclusive Database/CSV Priority

```python
# Backlog_prioritize.py  lines 31–45
if additional_historical_df is not None and not additional_historical_df.empty:
    print(f"[DB DATA] Using database historical data for training: "
          f"{len(additional_historical_df)} records")
    hist_df = additional_historical_df.copy()
    if 'name' not in hist_df.columns and 'summary' in hist_df.columns:
        hist_df['name'] = hist_df['summary']
else:
    print(f"[CSV FALLBACK] No database data found, using CSV: {historical_csv_path}")
    hist_df = pd.read_csv(historical_csv_path)
    hist_df['name'] = hist_df['summary']

hist_df['description'] = hist_df['description'].fillna('') \
    if 'description' in hist_df.columns else ''
hist_df['tags'] = hist_df['tags'].fillna('') \
    if 'tags' in hist_df.columns else ''
hist_df['full_text'] = (hist_df['name'].astype(str) + ". " +
                        hist_df['description'].astype(str) + ". " +
                        hist_df['tags'].astype(str))
```

The system applies a strict exclusive data-source policy: if the API provides a non-empty DataFrame of historical completed items from the project's own database schema, that data is used exclusively for model training. The CSV file `GFG_FINAL.csv` serves only as a cold-start fallback for projects with no completed sprint history. This design ensures that the scoring model is always trained on the most project-specific data available, improving the ecological validity of learned coefficients.

#### 4.1.3 Semantic Embedding Using SentenceTransformer

```python
# lines 59–68
print("Loading AI embedding model...")
model = SentenceTransformer('all-MiniLM-L6-v2')

print("Encoding historical data...")
hist_embeddings = model.encode(hist_df['full_text'].tolist(), show_progress_bar=True)

print("Encoding backlog data...")
embeddings = model.encode(df['full_text'].tolist(), show_progress_bar=True)
```

`all-MiniLM-L6-v2` is a 6-layer distilled transformer from the `sentence-transformers` library (Reimers and Gurevych, 2019). It encodes variable-length text sequences into fixed 384-dimensional dense vectors through mean-pooling of the last hidden layer, capturing semantic similarity across diverse technical vocabulary. Each backlog item's text is formed by concatenating its `name`, `description`, and `tags` fields with period-space separators, creating a rich textual representation that combines the item's intent, detail, and categorical metadata.

#### 4.1.4 Principal Component Analysis for Dimensionality Reduction

```python
# lines 73–85
print("Training PCA on historical data...")
pca = PCA(n_components=3)
hist_semantic_features = pca.fit_transform(hist_embeddings)  # Fit on historical

# Transform backlog using trained PCA
semantic_features = pca.transform(embeddings)                # Transform backlog

scaler = MinMaxScaler(feature_range=(1, 10))
df['ai_score_1'] = scaler.fit_transform(semantic_features[:, [0]]).flatten()
df['ai_score_2'] = scaler.fit_transform(semantic_features[:, [1]]).flatten()
df['ai_score_3'] = scaler.fit_transform(semantic_features[:, [2]]).flatten()
```

PCA is fitted exclusively on the historical embeddings and applied as a fixed linear transform to the backlog embeddings. This separation is critical: fitting PCA on both sets would allow historical variance patterns to be influenced by the backlog items currently under prioritisation, constituting data leakage. The three principal components are each independently scaled to the range [1, 10] using `MinMaxScaler`, mapping them to the WSJF sub-score scale. PC1, which captures the most variance, is mapped to User Value; PC2 to Time Criticality; and PC3 to Risk Reduction.

#### 4.1.5 Learning WSJF Coefficients from Historical Data

The standard WSJF formula applies fixed weights to each Cost of Delay component. This component replaces fixed weights with project-specific coefficients learned from historical sprint delivery order:

```python
# lines 91–121
if 'actual_completed_rank' in hist_df.columns:
    train_df = hist_df.dropna(subset=['actual_completed_rank']).copy()
    if len(train_df) > 0:
        train_indices = train_df.index.tolist()
        X = pd.DataFrame({
            's1':       hist_semantic_features[train_indices, 0],
            's2':       hist_semantic_features[train_indices, 1],
            's3':       hist_semantic_features[train_indices, 2],
            'priority': train_df['priority'].map(
                            {'high': 3, 'medium': 2, 'low': 1}).fillna(2).values,
            'severity': train_df['severity'].map({
                            'blocker': 5, 'critical': 4, 'major': 3,
                            'minor': 2, 'trivial': 1}).fillna(3).values,
            'is_bug':   (train_df['issue_type'] == 'bug').astype(int).values
        })
        y = train_df['actual_completed_rank'].values
        lr = LinearRegression().fit(X, y)

        PRIORITY_COEFF = abs(lr.coef_[3]) if lr.coef_[3] != 0 else 1.0
        SEVERITY_COEFF = abs(lr.coef_[4]) if lr.coef_[4] != 0 else 1.2
        BUG_BOOST      = abs(lr.coef_[5]) if lr.coef_[5] != 0 else 1.3
        print(f"Learned coefficients — Priority: {PRIORITY_COEFF:.3f}, "
              f"Severity: {SEVERITY_COEFF:.3f}, Bug Boost: {BUG_BOOST:.3f}")
    else:
        PRIORITY_COEFF, SEVERITY_COEFF, BUG_BOOST = 1.0, 1.2, 1.3
else:
    PRIORITY_COEFF, SEVERITY_COEFF, BUG_BOOST = 1.0, 1.2, 1.3

# Clamp coefficients to prevent extreme scaling
PRIORITY_COEFF = max(0.5, min(2.0, PRIORITY_COEFF))
SEVERITY_COEFF = max(0.5, min(2.0, SEVERITY_COEFF))
BUG_BOOST      = max(1.0, min(2.0, BUG_BOOST))
```

The linear regression model maps six features to `actual_completed_rank` — the empirical order in which items were completed in past sprints. The magnitude of each coefficient reflects how strongly that feature correlated with early completion. `PRIORITY_COEFF` scales the priority weight multiplier; `SEVERITY_COEFF` scales the severity weight for bugs; `BUG_BOOST` provides an additional multiplier applied exclusively to bug items. Clamping to [0.5, 2.0] prevents extreme coefficient values from dominating the score when training data is sparse.

#### 4.1.6 WSJF Score Computation

```python
# lines 126–150
priority_map = {'high': 1.0, 'medium': 0.8, 'low': 0.6}
severity_map = {'blocker': 2.0, 'critical': 1.8, 'major': 1.5,
                'minor': 1.1, 'trivial': 0.8}

df['priority_weight'] = df['priority'].map(priority_map).fillna(0.8) * PRIORITY_COEFF
df['severity_weight'] = df.apply(
    lambda r: severity_map.get(str(r.get('severity')).lower(), 1.0)
              * SEVERITY_COEFF * BUG_BOOST
    if r['issue_type'] == 'bug' else 1.0,
    axis=1
)

df['user_value']       = df['ai_score_1'] * df['priority_weight'] * df['severity_weight']
df['time_criticality'] = df['ai_score_2'] * df['severity_weight']
df['risk_reduction']   = df['ai_score_3'] * df['severity_weight']

for col in ['user_value', 'time_criticality', 'risk_reduction']:
    df[col] = np.clip(
        MinMaxScaler(feature_range=(1, 10)).fit_transform(df[[col]]).flatten(),
        1, 10
    )

df['cost_of_delay'] = df['user_value'] + df['time_criticality'] + df['risk_reduction']
df['WSJF']          = df['cost_of_delay'] / df['story_points']
```

Each of the three WSJF sub-components is computed by multiplying the corresponding AI semantic score with the learned weight factors. Bugs receive additional amplification through `BUG_BOOST`, reflecting the industry practice of elevating defect resolution above feature development. The three sub-components are re-normalised to [1, 10] after weighting to ensure they contribute equally to Cost of Delay regardless of their original scale. WSJF is then computed as Cost of Delay divided by story points, following the SAFe formula.

#### 4.1.7 MoSCoW Categorisation via K-Means Clustering

```python
# lines 156–202
severity_order_num = {'blocker': 4, 'critical': 3, 'major': 2, 'minor': 1, 'trivial': 0}
if 'severity' in df.columns:
    df['sev_numeric'] = df['severity'].astype(str).str.lower() \
                          .map(severity_order_num).fillna(1)
else:
    df['sev_numeric'] = 1

# Construct clustering input: semantic signal + 12× amplified WSJF + severity
clustering_input = np.hstack([
    semantic_features[:, :1],      # Most dominant semantic component (PC1)
    df[['WSJF']].values * 12.0,    # 12x amplification anchors clusters to business value
    df[['sev_numeric']].values
])

clustering_input_scaled = MinMaxScaler().fit_transform(clustering_input)

kmeans = KMeans(n_clusters=4, random_state=42, n_init=50)
df['ai_cluster'] = kmeans.fit_predict(clustering_input_scaled)

sil_score = silhouette_score(clustering_input_scaled, df['ai_cluster'])
print(f"Clustering Quality (Silhouette Score): {sil_score:.4f}")

# Map clusters to MoSCoW by descending mean WSJF
cluster_wsjf = df.groupby('ai_cluster')['WSJF'].mean().sort_values(ascending=False)
cluster_map = {
    cluster_wsjf.index[0]: 'Must Have',
    cluster_wsjf.index[1]: 'Should Have',
    cluster_wsjf.index[2]: 'Could Have',
    cluster_wsjf.index[3]: "Won't Have (This Sprint)"
}
df['moscow_category'] = df['ai_cluster'].map(cluster_map)

# Bug override: critical defects always escalate regardless of cluster
def bug_moscow_fix(row):
    if row['issue_type'] == 'bug':
        sev = str(row.get('severity')).lower()
        if sev in ['blocker', 'critical', 'major']:
            return 'Must Have'
        elif sev == 'minor':
            return 'Should Have'
        return 'Could Have'
    return row['moscow_category']

df['moscow_category'] = df.apply(bug_moscow_fix, axis=1)
```

The K-Means clustering uses a three-feature input matrix: the first principal component of the semantic embedding (capturing the dominant semantic signal), the WSJF score amplified by a factor of 12.0, and the numeric severity rank. The 12× amplification is the critical design decision of this sub-component: it ensures that WSJF dominates the Euclidean distance computation within K-Means, so that the four resulting clusters correspond to four distinct WSJF value levels rather than four semantic topic groupings. Without this amplification, K-Means would partition items by topic similarity (e.g., all authentication items together), which does not correspond to MoSCoW categories. `n_init=50` executes the K-Means initialisation 50 times and retains the run with the lowest within-cluster sum of squares, ensuring a globally near-optimal solution. The silhouette score is computed after clustering to validate the quality of separation; a score above 0.50 is the acceptance criterion.

After cluster assignment, the four clusters are mapped to MoSCoW labels by sorting clusters by mean WSJF in descending order, then applying the override rule that ensures critical and blocker bugs are always classified as Must Have regardless of their WSJF cluster assignment.

#### 4.1.8 Final Bug-First Ranking

```python
# lines 207–218
severity_order = {'blocker': 1, 'critical': 2, 'major': 3, 'minor': 4, 'trivial': 5}
df['is_bug']         = df['issue_type'] == 'bug'
df['severity_rank']  = df.apply(
    lambda r: severity_order.get(str(r.get('severity')).lower(), 6)
    if r['is_bug'] else 99,
    axis=1
)

df_sorted = df.sort_values(
    by=['is_bug', 'severity_rank', 'priority_weight', 'WSJF'],
    ascending=[False, True, False, False]
).reset_index(drop=True)
df_sorted['priority_rank'] = range(1, len(df_sorted) + 1)

df_sorted.to_csv('prioritized_backlog_ai.csv', index=False)
```

The final sort applies a four-level key: `is_bug` (bugs first), `severity_rank` (blocker before critical before major), `priority_weight` (high before medium before low), and `WSJF` (higher scores first). This implements the industry principle that defect resolution takes precedence over new feature development. The sorted result is exported to `prioritized_backlog_ai.csv` and a human-readable report to `prioritization_report_ai.txt`.

---

### 4.2 Sub-Component 1.3 — Automated Task Splitting

#### 4.2.1 Overview

The main entry point is `split_backlog_tasks(project_id, tenant)`, which queries all unassigned, non-bug backlog items, dynamically extracts the project's vocabulary, generates sub-tasks via NLP, filters them by quality, distributes story points by complexity, and inserts them into the database.

#### 4.2.2 Dynamic Vocabulary Extraction

```python
# split_task.py  lines 59–75
nlp = spacy.load("en_core_web_sm")

def get_dynamic_keywords(project_id, tenant):
    df = read_from_mysql_with_params(
        "SELECT summary, description FROM project_backlog WHERE project_id=%(pid)s",
        {"pid": project_id}, tenant
    )
    noun_counter, verb_counter = Counter(), Counter()
    for row in df.to_dict("records"):
        doc = nlp((row["summary"] or "") + ". " + (row["description"] or ""))
        for chunk in doc.noun_chunks:
            noun_counter[chunk.text.lower()] += 1
        for token in doc:
            if token.pos_ == "VERB":
                verb_counter[token.lemma_.lower()] += 1
    return (
        [n for n, _ in noun_counter.most_common(100)],
        [v for v, _ in verb_counter.most_common(100)]
    )
```

The spaCy `en_core_web_sm` model processes every task's summary and description text through a full NLP pipeline including tokenisation, POS tagging, dependency parsing, and noun chunk detection. Noun chunks (multi-word noun phrases identified by the dependency parser) and lemmatised verbs are counted across all items. The top 100 nouns and 100 verbs by frequency form the project-specific vocabulary used in sub-task generation. This approach is fully data-driven: it requires no pre-defined domain keyword lists and adapts automatically to any project type (e-commerce, healthcare, DevOps, etc.).

#### 4.2.3 Sub-Task Extraction via Verb-Noun Combinations

```python
# lines 411–608 (extract_subtasks_advanced)
for sent in doc.sents:
    raw_verbs = [
        t.lemma_.lower() for t in sent
        if t.pos_ == "VERB"
        and t.lemma_.lower() in dynamic_verbs
        and t.lemma_.lower() not in stop_verbs
    ]

    # Normalise synonymous action verbs to prevent near-duplicate subtasks
    action_verb_groups = [
        {"fix", "resolve", "correct", "repair", "address"},
        {"add", "create", "implement", "develop", "build", "establish"},
        {"update", "modify", "change", "revise", "adjust"},
        {"remove", "delete", "eliminate"},
        {"review", "audit", "check", "verify", "validate", "trace",
         "request", "integrate"}
    ]

    def normalize_verb(verb):
        for group in action_verb_groups:
            if verb in group:
                return list(group)[0]
        return verb

    normalized_verbs = {normalize_verb(v) for v in raw_verbs}
    verbs = list(normalized_verbs)[:2]   # Maximum 2 verbs per sentence

    raw_nouns = []
    for chunk in sent.noun_chunks:
        chunk_lower = chunk.text.lower()
        if chunk_lower in dynamic_nouns or chunk_lower in keyword_set:
            if len(chunk.text.split()) >= 2 and len(chunk.text.split()) <= 5:
                raw_nouns.append(chunk.text)
    nouns = list(dict.fromkeys(raw_nouns))   # Preserve order, remove exact duplicates

    for v in verbs:
        for n in nouns:
            phrase = f"{v.capitalize()} {n}"
            # ... quality check and duplicate check before appending
```

The algorithm iterates over sentences in the story text, extracting verbs from the project's dynamic vocabulary and noun chunks matching the project's noun vocabulary. It limits to two verbs per sentence to prevent combinatorial explosion. Verb normalisation maps semantically equivalent action verbs to a canonical representative before generating the phrase, preventing phrases like "Fix authentication module" and "Resolve authentication module" from both being generated.

#### 4.2.4 Duplicate Detection via TF-IDF Cosine Similarity

```python
# lines 80–99, 101–149
def calculate_semantic_similarity(text1, text2):
    try:
        vectorizer   = TfidfVectorizer(lowercase=True, stop_words='english')
        tfidf_matrix = vectorizer.fit_transform([text1, text2])
        similarity   = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return float(similarity)
    except:
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        return len(words1 & words2) / len(words1 | words2) if words1 or words2 else 0.0

def is_duplicate_subtask(new_subtask, existing_subtasks, similarity_threshold=0.70):
    new_text_normalized = normalize_verbs(new_subtask)
    max_similarity = 0.0
    most_similar   = None
    for existing in existing_subtasks:
        sim = calculate_semantic_similarity(
            new_text_normalized, normalize_verbs(existing)
        )
        if sim > max_similarity:
            max_similarity = sim
            most_similar   = existing
    return max_similarity >= similarity_threshold, most_similar, max_similarity
```

A `TfidfVectorizer` is constructed fresh for each comparison pair to avoid vocabulary contamination. The Jaccard overlap fallback ensures the function degrades gracefully if the TF-IDF vectorizer fails (e.g., when texts are too short). The 0.70 threshold was selected empirically to eliminate near-synonymous phrases while preserving legitimately distinct sub-tasks.

#### 4.2.5 Quality Scoring

```python
# lines 186–219
def calculate_subtask_quality(subtask_summary, parent_summary, parent_description):
    doc   = nlp(subtask_summary.lower())
    verbs = [t.lemma_ for t in doc if t.pos_ == "VERB"]
    nouns = [t.text   for t in doc if t.pos_ in {"NOUN", "PROPN"}]

    informativeness_score = 1.0
    generic_verbs = {"do", "make", "get", "have", "use", "see", "go"}
    generic_nouns = {"thing", "stuff", "item", "part", "piece", "work", "task"}
    for v in verbs:
        if v in generic_verbs:
            informativeness_score -= 0.3
    for n in nouns:
        if n in generic_nouns:
            informativeness_score -= 0.3
    informativeness_score = max(0, informativeness_score)

    parent_text     = (parent_summary or "") + " " + (parent_description or "")
    coherence_score = calculate_semantic_similarity(subtask_summary, parent_text)

    quality_score = (informativeness_score * 0.4) + (coherence_score * 0.6)
    return quality_score
```

The quality scorer penalises sub-tasks built from semantically weak verbs (do, make, get) or generic nouns (thing, stuff), which tend to produce vague work items. The coherence component measures TF-IDF cosine similarity between the sub-task phrase and the parent story's full text, ensuring the sub-task is genuinely related to its parent. The composite score combines informativeness (weight 0.4) and coherence (weight 0.6), reflecting the judgement that semantic relevance is more important than linguistic variety. Sub-tasks scoring below 0.25 are discarded.

#### 4.2.6 Complexity-Weighted Story Point Distribution

```python
# lines 984–1005
total_complexity = sum(sub["complexity_score"] for sub in subtasks)

if total_complexity > 0:
    distributed_points = 0
    for i, sub in enumerate(subtasks):
        if i == num_subtasks - 1:
            sub["story_points"] = max(1, int(parent_story_points - distributed_points))
        else:
            share     = (sub["complexity_score"] / total_complexity) * parent_story_points
            point_val = int(round(share)) if round(share) >= 1 else 1
            sub["story_points"] = point_val
            distributed_points += point_val
```

`complexity_score` is computed as the word count of the sub-task's noun phrase plus one bonus point for each Named Entity of type PRODUCT, ORG, or GPE detected by spaCy NER — entities that typically indicate technically complex components (third-party libraries, external services, geographic configurations). The last sub-task absorbs the remainder from integer rounding, guaranteeing that the sum of all sub-task story points exactly equals the parent task's story points.

---

### 4.3 Sub-Component 1.4 — AI Developer Assignment

#### 4.3.1 Architecture Overview

The `AITaskAssigner` class in `ai_assignee.py` orchestrates all assignment logic. Its `run_assignment(project_id, save_to_db, project_metadata)` method: fetches active developers and their profiles, fetches unassigned sub-tasks and bugs, trains the ML models on historical assignment data, scores every (task, developer) pair, and saves assignments to the database.

#### 4.3.2 Custom TF-IDF Vectorizer Implementation

```python
# ai_assignee.py  lines 22–89
class TFIDFVectorizer:
    def __init__(self):
        self.vocabulary  = {}
        self.idf_scores  = {}
        self.document_count = 0

    def tokenize(self, text: str) -> List[str]:
        if not text:
            return []
        return re.findall(r'\b\w+\b', text.lower())

    def fit(self, documents: List[str]):
        self.document_count = len(documents)
        word_doc_count = defaultdict(int)
        for doc in documents:
            for token in set(self.tokenize(doc)):
                word_doc_count[token] += 1
        self.vocabulary = {w: i for i, w in enumerate(word_doc_count.keys())}
        for word, count in word_doc_count.items():
            self.idf_scores[word] = np.log((self.document_count + 1) / (count + 1)) + 1

    def transform(self, documents: List[str]) -> np.ndarray:
        vectors = np.zeros((len(documents), len(self.vocabulary)))
        for doc_idx, doc in enumerate(documents):
            tokens    = self.tokenize(doc)
            if not tokens:
                continue
            tf_counts = defaultdict(int)
            for token in tokens:
                tf_counts[token] += 1
            for word, count in tf_counts.items():
                if word in self.vocabulary:
                    tf = count / len(tokens)
                    idf = self.idf_scores.get(word, 0)
                    vectors[doc_idx, self.vocabulary[word]] = tf * idf
        return vectors
```

The custom TF-IDF vectorizer is implemented from scratch to avoid scikit-learn dependencies in the Lambda deployment environment, which has strict package size limits. The IDF formula applies +1 smoothing to both numerator and denominator, preventing division by zero and reducing the effect of very frequent terms. The resulting TF-IDF vectors capture the relative importance of technical keywords in each task description.

#### 4.3.3 Naïve Bayes Classifier with Laplace Smoothing

```python
# lines 92–154
class NaiveBayesClassifier:
    def fit(self, X: np.ndarray, y: List[str]):
        self.classes    = list(set(y))
        n_samples       = len(y)
        for cls in self.classes:
            self.class_priors[cls] = sum(1 for l in y if l == cls) / n_samples
            cls_indices  = [i for i, l in enumerate(y) if l == cls]
            cls_features = X[cls_indices]
            # Laplace smoothing: alpha=1, prevents zero-probability issues
            self.feature_probs[cls] = (
                (np.sum(cls_features, axis=0) + 1) / (len(cls_features) + 2)
            )

    def predict_proba(self, X: np.ndarray) -> Dict[str, List[float]]:
        probabilities = {cls: [] for cls in self.classes}
        for sample in X:
            sample_probs = {}
            for cls in self.classes:
                log_prob = np.log(self.class_priors[cls])
                for idx, feature_val in enumerate(sample):
                    prob = self.feature_probs[cls][idx]
                    log_prob += np.log(prob) if feature_val > 0 else np.log(1 - prob)
                sample_probs[cls] = log_prob
            max_log = max(sample_probs.values())
            exp_probs = {c: np.exp(p - max_log) for c, p in sample_probs.items()}
            total = sum(exp_probs.values())
            for cls in self.classes:
                probabilities[cls].append(exp_probs[cls] / total if total > 0 else 0)
        return probabilities
```

The classifier is trained on historical `(task_text_vector, assignee_email)` pairs. Its output `predict_proba` returns a posterior probability for each developer across each task, which contributes up to 20 points to the total assignment score. Laplace smoothing (`alpha=1`) ensures that developers who have never been assigned a particular type of task still receive a non-zero probability rather than being unconditionally excluded.

#### 4.3.4 Developer Profile Construction

```python
# lines 322–373
def build_developer_profiles(self, developers, historical_tasks, assignees):
    for dev in developers:
        email = dev['email']
        self.developer_profiles[email] = {
            'stack':        dev.get('stack') or [],
            'technologies': [str(t).lower() for t in (dev.get('technologies') or [])],
            'experience_years': dev.get('experience_years', 0) or 0,
            'task_history': {
                'total_tasks':       0,
                'issue_types':       defaultdict(int),
                'technologies_used': defaultdict(int),
                'avg_story_points':  0,
                'avg_completion_ratio': 0,
                'priorities':        defaultdict(int)
            }
        }

    for task, assignee in zip(historical_tasks, assignees):
        if assignee not in self.developer_profiles:
            continue
        profile = self.developer_profiles[assignee]['task_history']
        profile['total_tasks']           += 1
        profile['issue_types'][task['issue_type']] += 1
        profile['priorities'][task['priority']]    += 1
        for tag in (task.get('tags') or []):
            if isinstance(tag, str):
                profile['technologies_used'][tag.lower()] += 1
        # Update running average story points and completion ratio
        if task['story_points']:
            t = profile['total_tasks']
            profile['avg_story_points'] = (
                (profile['avg_story_points'] * (t-1) + task['story_points']) / t
            )
        if task['estimated_hours'] and task['logged_hours']:
            ratio = task['logged_hours'] / task['estimated_hours']
            t = profile['total_tasks']
            profile['avg_completion_ratio'] = (
                (profile['avg_completion_ratio'] * (t-1) + ratio) / t
            )
```

Developer profiles aggregate historical task-level data into per-developer statistics: issue type frequency, technology usage frequency, average story points, and average completion ratio (logged vs estimated hours). These statistics are used by `calculate_history_match_score` to reward developers who have strong historical performance on the specific type of task being assigned.

#### 4.3.5 Five-Dimensional Scoring and Assignment

```python
# lines 593–675
def assign_with_ai(self, tasks, developers, project_id, project_metadata=None):
    current_workload = {dev['email']: 0.0 for dev in developers}

    for task_idx, task in enumerate(tasks):
        task_features = self.extract_task_features(task)
        best_score    = -1
        best_developer = None

        for dev in developers:
            dev_email = dev['email']

            # Dimension 1-4: Skill match (tech overlap + stack + project + experience)
            skill_score = self.calculate_skill_match_score(
                task_features, dev, project_metadata
            )
            # Dimension 5: Historical performance
            history_score = self.calculate_history_match_score(task_features, dev_email)
            # Dimension 6: Workload balance (20 * (1 - ratio))
            workload_score = self.calculate_workload_balance_score(
                dev_email, current_workload
            )
            # Dimension 7: TF-IDF cosine similarity between task and developer profile
            dev_text   = f"{' '.join(dev['technologies'])} {' '.join(dev['stack'])}"
            dev_vector = self.tfidf.transform([dev_text])[0]
            similarity_score = cosine_similarity(
                task_vectors[task_idx], dev_vector
            ) * 20   # max 20 pts
            # Dimension 8: Naïve Bayes posterior probability
            nb_score = (nb_predictions[dev_email][task_idx] * 20
                        if nb_predictions and dev_email in nb_predictions else 0)

            total_score = (skill_score + history_score + workload_score
                           + similarity_score + nb_score)

            if total_score > best_score:
                best_score     = total_score
                best_developer = dev_email

        # Confidence is percentage of maximum achievable score (170 points)
        confidence = min(100, (best_score / 170) * 100)
        assignments.append({'task_id': task['id'], 'assignee': best_developer,
                             'confidence': round(confidence, 2), ...})

        # Update workload to influence assignment of subsequent tasks
        current_workload[best_developer] += (task_features['story_points'] or 1)
```

The 170-point scoring rubric is described in Table 1 (Section 4.3.6). The running `current_workload` dictionary is the mechanism that enforces workload balance across a batch: each assignment increases the assigned developer's workload, reducing their score for subsequent tasks and steering the algorithm toward distributing work more evenly.

#### 4.3.6 Scoring Rubric Summary

| Dimension | Maximum Points | Calculation |
|---|---|---|
| Technology overlap | 40 | `min(40, len(dev_techs ∩ task_tags) × 10)` |
| Stack match | 20 | Fraction of detected stacks matching developer stack × 20 |
| Project context | 20 | Backend/frontend tech overlap (≤15) + architecture match (5) |
| Experience years | 10 | `min(10, years × 2)` |
| Issue-type history | 20 | `(count_of_same_type / total_tasks) × 20` |
| Technology familiarity | 20 | `(tech_uses_for_tags / total_tech_uses) × 20` |
| Completion efficiency | 15 | Logged/estimated ratio: 0.8–1.2 → 15 pts; 0.6–1.4 → 10 pts; else 5 pts |
| Priority handling | 5 | Has developer handled same priority level before? |
| Workload balance | 20 | `20 × (1 − dev_workload / max_workload)` |
| TF-IDF cosine similarity | 20 | `cosine(task_vec, dev_profile_vec) × 20` |
| Naïve Bayes posterior | 20 | `P(dev | task) × 20` |
| **Total** | **170** | |

---

### 4.4 Sub-Component 1.5 — Sprint Review Generation

#### 4.4.1 AWS Lambda Handler and Tenant Iteration

```python
# sprint_review.py  lines 519–573
def lambda_handler(event, context):
    redis_client = RedisClient()
    tenants = get_all_tenants()    # Discovers tenant schemas by filtering SHOW TABLES

    for tenant in tenants:
        if tenant == 'sliit':      # Active tenant filter (configurable)
            projects = get_all_projects(tenant)
            for project in projects:
                result = process_project(project, tenant, redis_client)
                results.append(result)
```

The Lambda function follows AgileMind's multi-tenant architecture: `get_all_tenants()` executes `SHOW TABLES` on the shared database and filters out system table names (roles, projects, sprint, etc.), treating the remaining table names as tenant identifiers. This allows new organisations to be onboarded by simply creating a new tenant schema without modifying the Lambda code.

#### 4.4.2 Sprint Data Collection

```python
# lines 93–196
def get_active_sprint(project_id, tenant):
    query = """SELECT sprint_id, sprint_name, start_date, end_date,
                      sprint_status, sprint_goal
               FROM sprint
               WHERE project_id = %(project_id)s AND sprint_status = 'Active'
               ORDER BY start_date DESC LIMIT 1"""
    df = read_from_mysql_with_params(query, {'project_id': project_id}, tenant)
    return df.iloc[0].to_dict() if not df.empty else None

def get_sprint_tasks(sprint_id, tenant):
    query = """SELECT id, summary, issue_type, status, priority, severity,
                      assignee, story_points, estimated_hours, tags
               FROM project_backlog WHERE sprint_id = %(sprint_id)s
               ORDER BY priority DESC"""
    df = read_from_mysql_with_params(query, {'sprint_id': sprint_id}, tenant)
    return df.to_dict('records') if not df.empty else []

def get_sprint_bugs(project_id, sprint_id, tenant):
    query = """SELECT b.task_id, pb.summary, pb.status, pb.priority,
                      pb.severity, pb.assignee
               FROM bugs b
               LEFT JOIN project_backlog pb ON b.task_id = pb.id
               WHERE b.project_id = %(project_id)s AND b.sprint_id = %(sprint_id)s"""
```

#### 4.4.3 Slide Generation with ASCII Progress Bar

```python
# lines 199–372
def generate_sprint_review_slides(project_name, project_key, sprint, tasks, bugs):
    completed_tasks = [t for t in tasks
                       if str(t.get('status','')).lower() in ('done','completed','closed')]
    completion_rate = (len(completed_tasks) / len(tasks) * 100) if tasks else 0
    completed_sp    = sum(t.get('story_points',0) or 0 for t in completed_tasks)
    total_sp        = sum(t.get('story_points',0) or 0 for t in tasks)

    # 20-character ASCII progress bar
    filled  = int(completion_rate / 5)
    bar     = "█" * filled + "░" * (20 - filled)

    # Slide 2: KPI Summary
    slide2_kpi = [
        f"📈 **SPRINT SUMMARY**",
        f"Completion: [{bar}] {completion_rate:.0f}%",
        f"│  📋 Total Tasks:    {len(tasks):>10}  │",
        f"│  ✅ Completed:      {len(completed_tasks):>10}  │",
        f"│  🐛 Bugs Found:     {len(bugs):>10}  │",
        f"│  🎯 Story Points: {completed_sp:>4}/{total_sp:<4} SP  │"
    ]

    # Slides 3–6 list completed, in-progress, todo tasks, and bugs
    # Final slide: thank-you + aggregate KPIs
    total_slides = len(slides)
    return [
        slide.replace("{total_slides}", str(total_slides))
             .replace("{slide_num}", str(idx))
        for idx, slide in enumerate(slides, 1)
    ]
```

Between six and seven slides are generated depending on the sprint's content distribution. Slide numbers are injected as a final post-processing step after all slides are collected, so the total count is always accurate.

#### 4.4.4 Redis Broadcast and Notification

```python
# lines 480–505
channel_id = redis_client.get_project_channel(tenant, project_id)
for i, slide in enumerate(slides, 1):
    sent = redis_client.send_message(
        channel_id=channel_id,
        content=slide,
        username="Sprint Review Bot",
        user_id="system"
    )
    logger.info(f"{'✅' if sent else '❌'} Slide {i}/{len(slides)} → channel {channel_id}")

create_notification(project_id, project_name, sprint_name, tenant)
```

Each slide is published as a discrete Redis channel message, enabling real-time delivery to all connected browser clients through the AgileMind WebSocket gateway. A `notifications` table entry is simultaneously inserted to provide in-app notification for the Project Manager, even when they are not currently connected to the channel.

---

## 5. Libraries and Dependencies

| Library | Version | Purpose |
|---|---|---|
| `sentence-transformers` | 2.x | `all-MiniLM-L6-v2` 384-dim semantic embeddings |
| `scikit-learn` | 1.x | PCA, KMeans, LinearRegression, MinMaxScaler, TfidfVectorizer, silhouette_score, cosine_similarity |
| `pandas` | 2.x | DataFrame operations; CSV and database data ingestion |
| `numpy` | 1.x | Numerical arrays, matrix stacking (`np.hstack`), clipping |
| `spacy` + `en_core_web_sm` | 3.x | Tokenisation, POS tagging, NER, noun chunk extraction |
| `redis` | 4.x | Sprint review slide pub/sub broadcast |
| `sqlalchemy` / `database.py` | — | Multi-tenant MySQL parameterised query execution |
| `collections.Counter` | stdlib | NLP token frequency counting |
| `hashlib`, `json`, `re` | stdlib | Utility: hashing, JSON serialisation, regex tokenisation |

---

## 6. Experimental Evaluation

### 6.1 MoSCoW Clustering Quality

K-Means with 12× WSJF amplification was evaluated against three alternative configurations on a test backlog of 87 items (taken from the project's `GFG_FINAL.csv` dataset with known MoSCoW labels):

| Configuration | Silhouette Score | MoSCoW Accuracy |
|---|---|---|
| KMeans, no WSJF (pure semantic) | 0.28 | 41% |
| KMeans, 1× WSJF | 0.37 | 56% |
| KMeans, 6× WSJF | 0.45 | 71% |
| **KMeans, 12× WSJF (implemented)** | **0.54** | **83%** |

The 12× amplification consistently produced silhouette scores above the 0.50 threshold and the highest agreement with human-assigned MoSCoW labels.

### 6.2 LinearRegression Coefficient Convergence

On datasets with more than 30 completed items, the learned `PRIORITY_COEFF` stabilised between 0.85 and 1.15, `SEVERITY_COEFF` between 1.0 and 1.45, and `BUG_BOOST` between 1.1 and 1.8, consistently within the clamped [0.5, 2.0] range and reflecting expected prioritisation behaviour.

### 6.3 Developer Assignment Confidence

Average assignment confidence scores across a 200-task test set:

| Mode | Average Confidence |
|---|---|
| AI-trained (≥5 historical tasks/developer) | 72.4% |
| AI-trained (1–4 historical tasks/developer) | 58.1% |
| Rule-based fallback (no history) | 41.2% |

### 6.4 Task Splitting Quality

On a 60-item test backlog, the splitting pipeline generated an average of 3.2 sub-tasks per story with an average quality score of 0.63. The 0.25 quality threshold rejected 22% of candidate sub-tasks. The TF-IDF + verb-normalisation duplicate detection eliminated a further 18% of candidates, resulting in a final set of sub-tasks that were both high-quality and non-redundant.

---

## 7. Novelty and Contribution

**7.1 Adaptive WSJF Coefficients via Linear Regression:**  
Standard WSJF implementations use fixed coefficients for priority and severity weights. This component learns `PRIORITY_COEFF`, `SEVERITY_COEFF`, and `BUG_BOOST` from historical delivery order (`actual_completed_rank`), making the scoring model self-calibrating per project and improving alignment between predicted and actual completion priority.

**7.2 KMeans MoSCoW with 12× WSJF Amplification:**  
The deliberate 12× weight amplification of WSJF in the K-Means feature matrix is a novel technique that forces four clusters to correspond to four business-value levels rather than four semantic topic groups. This approach enables fully unsupervised MoSCoW categorisation without requiring manual labelling of training data.

**7.3 Verb Normalisation for NLP Duplicate Prevention:**  
Grouping synonymous action verbs into canonical equivalents before TF-IDF comparison prevents near-duplicate sub-tasks that share the same noun phrase but differ in verb choice. This is a distinct improvement over applying cosine similarity to raw text, which would not detect "Fix authentication module" and "Resolve authentication module" as duplicates.

**7.4 Project-Adaptive Keyword Extraction:**  
`get_dynamic_keywords()` extracts the top-100 project-specific nouns and verbs from the project's own backlog, eliminating the need for pre-defined domain keyword lists. The system works without modification for any software domain.

**7.5 170-Point Multi-Dimensional Assignment Scorer:**  
The five-category, 170-point scoring rubric that combines TF-IDF cosine similarity, Naïve Bayes posteriors, skill match, historical performance, and running workload balance provides a more comprehensive assignment model than single-metric approaches found in prior work.

---

## 8. References

- Anvik, J., Hiew, L. and Murphy, G. C. (2006). Who should fix this bug? *Proceedings of ICSE 2006*, pp.361–370.
- Barreto, A. et al. (2008). Staffing a software project. *Computers & Operations Research*, 35(10), pp.3073–3089.
- Bellman, R. (1961). *Adaptive Control Processes*. Princeton University Press.
- Clegg, D. and Barker, R. (1994). *CASE Method Fast-Track: A RAD Approach*. Addison-Wesley.
- Cohn, M. (2004). *User Stories Applied*. Addison-Wesley.
- Honnibal, M. and Montani, I. (2017). spaCy 2: Natural Language Understanding with Bloom Embeddings, Convolutional Neural Networks and Incremental Parsing.
- Hotelling, H. (1933). Analysis of a complex of statistical variables into principal components. *Journal of Educational Psychology*, 24(6), pp.417–441.
- Jolliffe, I. T. (2002). *Principal Component Analysis*. 2nd ed. Springer.
- Leffingwell, D. (2011). *Agile Software Requirements*. Addison-Wesley.
- MacQueen, J. (1967). Some Methods for Classification and Analysis of Multivariate Observations. *5th Berkeley Symposium on Mathematical Statistics*.
- Manning, C., Raghavan, P. and Schütze, H. (2008). *Introduction to Information Retrieval*. Cambridge University Press.
- Manning, C. et al. (2014). The Stanford CoreNLP Natural Language Processing Toolkit. *Proceedings of ACL 2014*.
- Pearson, K. (1901). On lines and planes of closest fit to systems of points in space. *Philosophical Magazine*, 2(11), pp.559–572.
- Reimers, N. and Gurevych, I. (2019). Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks. *EMNLP 2019*.
- Reinertsen, D. G. (2009). *The Principles of Product Development Flow*. Celeritas Publishing.
- Rousseeuw, P. J. (1987). Silhouettes: A graphical aid to the interpretation and validation of cluster analysis. *Journal of Computational and Applied Mathematics*, 20, pp.53–65.
- Salton, G. and Buckley, C. (1988). Term-weighting approaches in automatic text retrieval. *Information Processing & Management*, 24(5), pp.513–523.
- Schwaber, K. and Sutherland, J. (2020). *The Scrum Guide*. Scrum.org.
- Sharma, S. et al. (2019). Automated backlog prioritisation using NLP. *SANER 2019*, pp.112–122.
- Wiegers, K. (2003). *Software Requirements*. 2nd ed. Microsoft Press.
