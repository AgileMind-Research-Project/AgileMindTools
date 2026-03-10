# 🤖 AI Backlog Prioritization System: Complete Technical Manifesto

## 📄 Executive Summary
The **AI Backlog Prioritization System** is an event-driven intelligence layer designed for the **AgileMindTools** platform. It automates the complex decision-making process of sprint planning by using **NLP-driven WSJF (Weighted Shortest Job First)** scoring and **Historical Behavioral Learning**.

---

## 🛠️ Complete Technology Stack

| Layer | Component | Description |
| :--- | :--- | :--- |
| **Machine Learning** | `Sentence-Transformers` | **Model: all-MiniLM-L6-v2**. Encodes tasks into 384D semantic embeddings. |
| **Feature Engineering** | `Scikit-Learn (PCA)` | Reduces complex embeddings into 3 core AI scores (User Value, Risk, Urgency). |
| **Clustering Engine** | `Scikit-Learn (K-Means)` | Assigns **MoSCoW** categories via unsupervised clustering (4 centers). |
| **Predictive Learning** | `Scikit-Learn (Linear Regression)` | Learns team-specific weights from `actual_completed_rank` data. |
| **Data Processing** | `Pandas & NumPy` | Handles large-scale matrix transformations and dataset harmonization. |
| **Database Layer** | `SQLAlchemy & PyMySQL` | Provides ORM-like connectivity and high-performance SQL execution. |
| **Serialization** | `JSON / Python-Dotenv` | Handles dynamic tag parsing and secure environment management. |
| **Deployment** | `AWS Lambda / Docker` | Fully containerized serverless architecture for scheduled execution. |

---

## 🔄 The End-to-End process

### Phase 1: Automated Discovery (Triggered 4 Days Before Sprint)
1.  **Event Trigger**: Triggered by a scheduled task (CloudWatch/Cron) or API call.
2.  **Project Filtering**: Identifies projects starting a new sprint in exactly **4 days** using `next_sprint_start_date`.
3.  **Backlog Harvesting**: Fetches unassigned items (`sprint_id IS NULL`) with statuses `todo` or `in_progress`.

### Phase 2: Hybrid Training Strategy
*   **Cold Start Memory**: Uses `GFG_FINAL.csv` as a baseline if the project is new.
*   **Dynamic Learning**: Queries the `project_backlog_priority` table to find the **last 3+ completed sprints**.
*   **Coefficient Auto-Tuning**: A **Linear Regression** model analyzes past "Actual Ranks" vs. "Initial Priorities" to adjust the **Bug Boost (1.0-2.0x)** and **Severity Multiplier**.

### Phase 3: Semantic Valuation & WSJF
1.  **Embedding**: Combines `Summary + Description + Tags` into a "Full Text" semantic string.
2.  **PCA Scoring**:
    *   **Score 1 (User Value)**: Derived from the primary semantic variance.
    *   **Score 2 (Time Criticality)**: Derived from secondary urgency cues.
    *   **Score 3 (Risk Reduction)**: Derived from technical complexity indicators.
3.  **WSJF Calculation**: 
    $$\text{WSJF} = \frac{(\text{User Value} \times \text{PrioWeight}) + (\text{Urgency} \times \text{SevWeight})}{\text{Story Points}}$$

### Phase 4: Prioritization Policies
*   **Bug-First Override**: All Bugs (Blocker/Critical/Major) are force-filtered to the top of the queue.
*   **MoSCoW Mapping**: KMeans clusters the remaining items into **Must/Should/Could/Won't** buckets based on their semantic density.
*   **Top-15 Truncation**: To prevent scope creep, only the highest **15 items** are saved for the next sprint review.

### Phase 5: Persistence & Communication
1.  **SQL Persistence**: Uses `ON DUPLICATE KEY UPDATE` to ensure rankings are updated if already exists.
2.  **CSV Archive**: A timestamped CSV file is archived for manual auditing.
3.  **Stakeholder Alert**: Inserts a `SUCCESS` notification in the DB targetted at specific emails parsed from the `project_manager` JSON list.

---

## 🔒 Security & Performance
*   **Credential Masking**: Uses `.env` and `keys.py` to prevent hardcoded secrets.
*   **Error Resiliency**: Includes a multi-layer fallback system (DB Data ➔ CSV Data ➔ Default Coefficients).
*   **SQL Safety**: All queries use parameterized inputs to prevent injection attacks.

---

## 📁 Key File Map
*   📁 `Backlog_prioritize.py`: The "Brain" (ML logic & WSJF).
*   📁 `get_upcoming_sprint_items.py`: The "Scout" (Data fetching & filtering).
*   📁 `prioritize_upcoming_sprints.py`: The "Orchestrator" (Integration & Database).
*   📁 `database.py`: The "Heart" (Database connections & query handling).
*   📁 `GFG_FINAL.csv`: The "Memory" (Historical training baseline).

---
*© 2026 AgileMindTools | AI-Driven Agile Excellence*
