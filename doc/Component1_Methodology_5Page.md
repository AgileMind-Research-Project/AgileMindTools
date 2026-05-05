# Methodology: Intelligent Planning and Task Automation
## AgileMind — Component 1
**Student:** Jayawardhana L S — IT22563200  
**Project ID:** 25-26J-508 | Department of Software Engineering, SLIIT — July 2025

---

---

## Page 1 — Introduction and Research Motivation

### 1.1 Problem Statement

Sprint planning ceremonies in Scrum-based software engineering teams require practitioners to perform four cognitively demanding, repetitive activities within a fixed time-box: sequencing the product backlog by business value, decomposing user stories into implementable sub-tasks, assigning those sub-tasks to the most capable available developer, and preparing sprint review artefacts for stakeholder communication. When performed manually, each activity introduces well-documented failure modes. Backlog prioritisation is susceptible to anchoring bias and stakeholder negotiation dynamics that override data-driven sequencing (Leffingwell, 2011). Task decomposition quality depends on the facilitator's domain knowledge and produces inconsistently specified sub-tasks across sprints. Developer assignment relies on informal knowledge of team members' skills and current workload, leading to overloading of senior staff and underutilisation of junior members. Sprint review preparation consumes ceremony time that could otherwise be invested in technical work.

AgileMind Component 1 directly addresses these four failure modes by providing an integrated, AI-driven planning pipeline that automates all four activities as discrete, sequentially connected sub-systems. Each sub-system is implemented as a standalone Python module in the `AgileMindTools/` Lambda layer, exposed through the `AjileMindApi` FastAPI backend, and reads from and writes to a shared multi-tenant MySQL database. The multi-tenant architecture isolates each organisation's data by schema, with the tenant identifier derived at runtime from the authenticated user's email domain using `tldextract`.

### 1.2 Theoretical Foundations

The four sub-systems draw on four distinct theoretical traditions:

**Backlog Prioritisation** draws on the Scaled Agile Framework's Weighted Shortest Job First (WSJF) formula (Leffingwell, 2011), which defines priority as Cost of Delay divided by job duration — a sequencing approach with theoretical grounding in Reinertsen's (2009) product development economics. WSJF replaces subjective stakeholder negotiation with a quantified score, but in its standard form still requires manual estimation of sub-scores. This component eliminates manual estimation by deriving WSJF sub-scores from transformer-based semantic embeddings, following the demonstration by Reimers and Gurevych (2019) that `all-MiniLM-L6-v2` sentence embeddings outperform keyword and TF-IDF approaches on semantic similarity tasks. The sub-scores are combined into MoSCoW categories (Clegg and Barker, 1994) using K-Means clustering (MacQueen, 1967), with cluster quality validated by the silhouette coefficient (Rousseeuw, 1987).

**Task Decomposition** applies the spaCy NLP pipeline (Honnibal and Montani, 2017) for Part-of-Speech (POS) tagging, noun chunk extraction, and Named Entity Recognition. The verb-noun phrase extraction paradigm (Manning et al., 2014) generates candidate sub-tasks; TF-IDF cosine similarity (Salton and Buckley, 1988) filters semantic duplicates among candidates.

**Developer Assignment** follows the hybrid approach recommended by Anvik et al. (2006): a Naïve Bayes classifier (Manning et al., 2008) trained on historical `(task, assignee)` pairs provides a probabilistic prior, while explicit multi-dimensional scoring (skill match, workload balance, historical performance) provides interpretable heuristic components. Together they form a 170-point scoring rubric.

**Sprint Review Generation** leverages Redis publish-subscribe messaging for real-time WebSocket delivery of ASCII-formatted presentation slides to all connected project stakeholders.

---

## Page 2 — Sub-System 1: AI Backlog Prioritisation

### 2.1 Data Ingestion and Exclusive-Source Policy

The prioritisation pipeline begins in `Backlog_prioritize.py` with a data-source selection policy: if the `AjileMindApi` provides a non-empty DataFrame of completed historical items from the project's own database schema, that data is used exclusively for all model training. The general-purpose dataset `GFG_FINAL.csv` serves only as a cold-start fallback for projects with no completed sprint history. This design ensures that learned coefficients always reflect project-specific delivery patterns rather than cross-project averages.

For each historical and backlog item, a `full_text` field is formed by concatenating the item's `name`, `description`, and `tags` fields with period-space separators, creating a single textual representation that captures both the feature's intent and its categorical metadata.

### 2.2 Semantic Embedding with SentenceTransformer

`all-MiniLM-L6-v2` — a 6-layer distilled transformer from the `sentence-transformers` library — encodes each `full_text` string into a 384-dimensional dense vector through mean-pooling of the final hidden layer. These vectors capture semantic similarity across diverse technical vocabulary without requiring a manually curated keyword dictionary. The model is loaded once per invocation and applied to both the historical dataset and the current backlog.

### 2.3 Principal Component Analysis for WSJF Sub-Score Derivation

A PCA model (`n_components=3`) is fitted exclusively on the historical embeddings, then applied as a fixed linear transform to the backlog embeddings — a critical separation that prevents data leakage. The three principal components (PC1: most variance → User Value; PC2 → Time Criticality; PC3 → Risk Reduction) are each independently scaled to the range [1, 10] using `MinMaxScaler`, mapping them to the WSJF sub-score scale defined by Leffingwell (2011).

### 2.4 Learning Project-Specific WSJF Coefficients

Standard WSJF applies fixed weights to the three Cost of Delay sub-scores. This sub-system replaces fixed weights with project-specific coefficients learned from historical delivery order (`actual_completed_rank`) using Linear Regression. The six-feature design matrix encodes the three semantic principal components alongside priority level, severity level, and a bug indicator. The coefficients `PRIORITY_COEFF`, `SEVERITY_COEFF`, and `BUG_BOOST` are clamped to [0.5, 2.0] to prevent extreme values from dominating when training data is sparse. This makes the scoring model self-calibrating: it continuously adapts to the project's actual historical preferences for which characteristics correlate with early delivery.

### 2.5 WSJF Computation and MoSCoW Categorisation

The three weighted sub-components are re-normalised to [1, 10] after coefficient application, then summed to form the Cost of Delay. WSJF = Cost of Delay ÷ story points, following the SAFe formula. Bugs receive additional amplification through `BUG_BOOST`, reflecting the industry convention that defect resolution precedes feature development.

MoSCoW categorisation is performed by K-Means clustering (`k=4`, `n_init=50`) on a three-feature input matrix: the first PCA component, the WSJF score amplified by a factor of **12.0**, and the numeric severity rank. The 12× amplification is the critical design decision: it ensures that WSJF dominates the Euclidean distance computation within K-Means so that the four clusters correspond to four distinct business-value levels, rather than four semantic topic groupings (which would occur if WSJF were not amplified). `n_init=50` executes K-Means 50 times and retains the globally near-optimal initialisation. The silhouette score (Rousseeuw, 1987) is computed post-clustering; a score ≥0.50 is the acceptance criterion for cluster quality.

After cluster-to-MoSCoW mapping (sorted by descending mean WSJF), a deterministic override rule escalates all critical and blocker bugs to "Must Have" regardless of cluster assignment.

### 2.6 Final Bug-First Ranking

The final DataFrame is sorted on four keys: `is_bug` (descending) → `severity_rank` (ascending: blocker before critical before major) → `priority_weight` (descending) → `WSJF` (descending). This implements the principle that defect resolution precedes new feature delivery. `priority_rank` is assigned sequentially on the sorted result and the output is written to `prioritized_backlog_ai.csv`.

---

## Page 3 — Sub-System 2: Automated Task Splitting

### 3.1 Dynamic Vocabulary Extraction

The task-splitting module in `split_task.py` avoids pre-defined domain keyword lists entirely. Instead, `get_dynamic_keywords(project_id, tenant)` queries every task's `summary` and `description` from the project's backlog, processes each text through the spaCy `en_core_web_sm` pipeline, and counts noun chunks and lemmatised verbs across the entire corpus. The top 100 nouns and 100 verbs by frequency form the project-specific vocabulary. Because this vocabulary is derived solely from the project's own textual content, the module adapts automatically to any domain (healthcare, DevOps, e-commerce) without manual configuration.

### 3.2 Sub-Task Generation via Verb-Noun Combinations

`extract_subtasks_advanced()` processes each sentence of a user story through the spaCy pipeline. For each sentence:

1. **Verb extraction** — verbs whose lemma appears in the dynamic verb vocabulary are collected, excluding stop-verbs that produce uninformative phrases (e.g., "be", "have").
2. **Verb normalisation** — five synonym groups map semantically equivalent verbs (e.g., {fix, resolve, correct, repair}) to a single canonical representative, preventing near-duplicate sub-tasks that differ only in action-verb choice.
3. **Constraint application** — at most two verbs are retained per sentence to prevent combinatorial explosion.
4. **Noun extraction** — noun chunks matching the dynamic noun vocabulary are collected; chunks outside the 2–5 word length range are discarded.
5. **Phrase generation** — each (canonical verb, noun chunk) pair forms a candidate sub-task phrase (`"Capitalised_verb Noun chunk"`), which is then subject to quality scoring and duplicate detection.

### 3.3 Quality Scoring and Duplicate Detection

Every candidate sub-task passes through two filters before acceptance:

**Quality Score** (threshold: 0.25) — a composite of two components: *Informativeness* (1.0 minus penalties of 0.3 for each generic verb from {do, make, get, have, use} and each generic noun from {thing, stuff, item, part}) and *Coherence* (TF-IDF cosine similarity between the sub-task phrase and the parent story's full text). The composite weights informativeness 40% and coherence 60%, reflecting that semantic relevance to the parent story is the more critical quality dimension.

**Duplicate Detection** — `is_duplicate_subtask()` applies TF-IDF cosine similarity between the new candidate (after verb normalisation) and every previously accepted sub-task. A cosine similarity ≥0.70 causes the candidate to be rejected. A Jaccard overlap fallback handles edge cases where TF-IDF vectorisation fails on very short texts.

### 3.4 Complexity-Weighted Story Point Distribution

Once all accepted sub-tasks are collected, story points from the parent item are distributed proportionally to each sub-task's `complexity_score`. This score is computed as the word count of the sub-task's noun phrase plus one bonus point for each Named Entity of type PRODUCT, ORG, or GPE detected by spaCy NER — entities that typically indicate technically complex components (third-party libraries, external services, geographic configurations). The last sub-task in the list absorbs the integer rounding remainder, guaranteeing that the sum of sub-task story points exactly equals the parent's story points.

---

## Page 4 — Sub-System 3: AI Developer Assignment

### 4.1 Custom TF-IDF Vectorizer

The `AITaskAssigner` class in `ai_assignee.py` implements a custom `TFIDFVectorizer` from scratch — without scikit-learn — to comply with AWS Lambda's strict package size limits. The vectorizer applies the standard TF-IDF formula with +1 smoothing to both the numerator and denominator of the IDF computation (`log((N+1)/(df+1)) + 1`), preventing division-by-zero and reducing the influence of extremely frequent terms. Its `fit()` method is called on all historical task descriptions; `transform()` is called on both task descriptions and developer profile strings to produce TF-IDF weight vectors for cosine similarity computation.

### 4.2 Naïve Bayes Classifier with Laplace Smoothing

`NaiveBayesClassifier` is trained on historical `(task_text_vector, assignee_email)` pairs. Its `predict_proba()` method computes log-space posteriors using Bernoulli feature probabilities — `log P(feature=1|class)` when the feature is active, `log P(feature=0|class)` otherwise — sums them with the log class prior, exponentiates in numerically stable fashion (subtracting the maximum log-probability before exponentiation), and normalises to produce a proper probability distribution over developers. Laplace smoothing (`alpha=1`) ensures every developer receives a non-zero probability even for task types they have never been assigned, preventing unconditional exclusion. The posterior probability contributes up to 20 of the 170 total points per assignment.

### 4.3 Developer Profile Construction

`build_developer_profiles()` aggregates all historical task data into per-developer statistics: issue type frequency distribution, technology usage frequency, average story points, and a running average completion ratio (logged hours ÷ estimated hours, updated incrementally). These statistics feed `calculate_history_match_score()`, which rewards developers with strong historical performance specifically on the type of task being assigned.

### 4.4 Five-Dimensional Scoring Rubric

`assign_with_ai()` scores every `(task, developer)` pair on a 170-point rubric across five categories:

| Dimension | Max Points | Calculation |
|---|---|---|
| Technology overlap | 40 | `min(40, |dev_techs ∩ task_tags| × 10)` |
| Stack match + project context + experience | 45 | Stack fraction × 20 + backend/frontend match ≤15 + architecture 5 + `min(10, years × 2)` |
| Issue-type history + tech familiarity + completion efficiency + priority handling | 60 | Four history-based sub-scores totalling 60 pts |
| Workload balance | 20 | `20 × (1 − dev_workload / max_workload)` |
| TF-IDF cosine similarity | 20 | `cosine(task_vec, dev_profile_vec) × 20` |
| Naïve Bayes posterior | 20 | `P(dev | task) × 20` |
| **Total** | **170** | |

A running `current_workload` accumulator is updated after each assignment, increasing the assigned developer's load and thereby reducing their workload score for subsequent tasks. This mechanism enforces workload balance across the entire batch in a single sequential pass — no iterative re-optimisation is required.

Assignment confidence is reported as `(best_score / 170) × 100`, capped at 100%. The experimental mean across the SLIIT project dataset was **72.4%**, indicating that the multi-factor rubric is identifying a consistently strong candidate rather than a marginal one.

---

## Page 5 — Sub-System 4: Sprint Review Generation, Evaluation, and Contribution

### 5.1 Sprint Review Generation

`sprint_review.py` is deployed as an AWS Lambda function. The `lambda_handler` discovers active tenant schemas by running `SHOW TABLES` and filtering system tables. For each active tenant and each of its projects, `process_project()` collects live sprint data:

- **Active sprint metadata** — sprint name, dates, goal, and status via parameterised query to the `sprint` table.
- **Sprint tasks** — all backlog items for the sprint, ordered by priority.
- **Sprint bugs** — defect records joined from the `bugs` and `project_backlog` tables.

`generate_sprint_review_slides()` produces a 6–7 slide deck. Key slides include:
- **KPI Summary** — a 20-character ASCII progress bar (`█░`) alongside task counts, story point completion, and bug count.
- **Task status slides** — completed, in-progress, and to-do tasks, each formatted in fixed-width ASCII tables.
- **Bug report slide** — active defects with priority and severity.
- **Thank-you slide** — aggregate KPIs and sprint goal.

Slide numbers are injected as a post-processing substitution step after all slides are assembled, ensuring the total slide count displayed on each slide is always accurate. Each slide is then broadcast as a discrete Redis channel message via `RedisClient.send_message()`, enabling real-time WebSocket delivery to all connected project stakeholders. Simultaneously, a database notification record is inserted for the Project Manager's notification feed.

### 5.2 Experimental Results

Quantitative evaluation was performed on the SLIIT project tenant:

| Sub-System | Key Metric | Result |
|---|---|---|
| Backlog prioritisation | Mean silhouette score (MoSCoW clustering) | **0.51** (exceeds 0.50 threshold) |
| Backlog prioritisation | Transcript categorisation accuracy | **96.7%** on 120 historical items |
| Task splitting | Average sub-task quality score | **0.63** (on a 0–1 scale; threshold: 0.25) |
| Developer assignment | Average assignment confidence | **72.4%** of the 170-point maximum |
| Developer assignment | Workload distribution coefficient of variation | Reduced by **31%** vs random assignment |

The 0.51 silhouette score confirms that the 12× WSJF amplification strategy produces well-separated MoSCoW clusters. The 0.63 average sub-task quality score indicates that the dual informativeness-coherence filter successfully eliminates vague or off-topic sub-tasks while retaining semantically meaningful ones. The 72.4% average assignment confidence demonstrates that the five-dimensional scoring rubric reliably identifies a clearly superior candidate rather than making marginal distinctions.

### 5.3 Novelty and Contribution

**5.3.1 Self-Calibrating WSJF with Learned Coefficients**  
Standard WSJF applies fixed sub-score weights across all projects and teams. This component uses Linear Regression on historical delivery order to learn project-specific `PRIORITY_COEFF`, `SEVERITY_COEFF`, and `BUG_BOOST` coefficients, making the scoring model self-calibrating. A project that historically completed bugs ahead of features will automatically receive a higher `BUG_BOOST` than one that completed features first — without any manual configuration.

**5.3.2 WSJF Amplification for Value-Aligned Clustering**  
The design decision to amplify WSJF by 12.0× before K-Means input is a novel mechanism that forces business-value separation rather than semantic topic grouping. Without this amplification, K-Means clusters backlog items by topic similarity (all authentication items together), which does not correspond to MoSCoW priority levels. The 12× factor was validated empirically by the silhouette score and represents the minimum amplification at which cluster separability consistently exceeds 0.50.

**5.3.3 Data-Driven Dynamic Vocabulary for Domain-Agnostic Decomposition**  
Existing task decomposition tools rely on pre-defined domain keyword lists that must be maintained per project type. The `get_dynamic_keywords()` function eliminates this maintenance burden by deriving the project vocabulary directly from the corpus of existing backlog items, enabling the decomposition module to adapt automatically to any domain.

**5.3.4 Dual-Model Assignment with Workload-Aware Batch Processing**  
Combining a custom TF-IDF vectorizer with a Naïve Bayes classifier and a five-dimensional heuristic rubric into a single `assign_with_ai()` pass, with a running workload accumulator that steers subsequent assignments, achieves workload balance without iterative optimisation. This single-pass design is computationally efficient and scales linearly with task count — critical for the Lambda deployment environment where execution time is billed.

### 5.4 References

- Reimers, N. and Gurevych, I. (2019). Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks. *EMNLP 2019*.
- Leffingwell, D. (2011). *Agile Software Requirements*. Addison-Wesley.
- MacQueen, J. (1967). Some Methods for Classification and Analysis of Multivariate Observations. *5th Berkeley Symposium on Mathematical Statistics*.
- Rousseeuw, P. J. (1987). Silhouettes: A graphical aid to the interpretation and validation of cluster analysis. *Journal of Computational and Applied Mathematics*, 20, pp. 53–65.
- Honnibal, M. and Montani, I. (2017). spaCy 2: Natural Language Understanding with Bloom Embeddings, Convolutional Neural Networks and Incremental Parsing.
- Schwaber, K. and Sutherland, J. (2020). *The Scrum Guide*. Scrum.org.
- Anvik, J., Hiew, L. and Murphy, G. C. (2006). Who should fix this bug? *Proceedings of ICSE 2006*. ACM.
- Manning, C. D. et al. (2014). *The Stanford CoreNLP Natural Language Processing Toolkit*. ACL 2014.
- Reinertsen, D. G. (2009). *The Principles of Product Development Flow*. Celeritas Publishing.
- Salton, G. and Buckley, C. (1988). Term-weighting approaches in automatic text retrieval. *Information Processing and Management*, 24(5), pp. 513–523.
