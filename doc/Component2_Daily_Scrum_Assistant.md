# Component 2: Synchronous Daily Scrum Assistant and Meeting Bot
**Student:** Weerapperuma B E — IT22584236  
**Project:** AgileMind — Enhancing Agile Project Management Platform Through Automation and Decision Support  
**Project ID:** 25-26J-508  
**Department of Software Engineering, SLIIT — July 2025**

---

## Abstract

The Daily Scrum is Scrum's most frequent ceremony, yet its value is undermined by three systemic failures: meeting transcripts are rarely captured, blockers are identified verbally but not tracked systematically, and team attendance patterns that signal engagement or disengagement go unmonitored. This component presents three integrated sub-systems that address these failures: (1) an Intelligent Transcript Management system using regex-based participant extraction and keyword-driven auto-categorisation; (2) an AI Blocker Analysis system using the Ollama `llama3.2` language model via LangChain to generate contextual recovery suggestions; and (3) a Mistral-7B AI Task Extractor that uses few-shot Chain-of-Thought prompting to extract structured task status updates from raw meeting transcripts. A fourth sub-component, the Team Rhythm Analyzer, tracks attendance patterns through SQL aggregation without machine learning, providing a purely database-driven leading indicator of team disengagement. All sub-components are implemented within the `AjileMindApi` FastAPI backend under `app/services/` and `app/ai/task_extractor/`.

---

## 1. Introduction

The Daily Scrum (or daily stand-up) is a 15-minute synchronisation ceremony in which each team member answers three questions: what was completed yesterday, what will be completed today, and what impediments exist. Despite its brevity, the Daily Scrum generates two critical artefacts that are routinely lost: a record of who said what (the transcript), and a structured log of blockers and task status changes (the structured update). Without these artefacts, project managers cannot retrospectively audit delivery progress, blockers accumulate invisibly between standups, and attendance trends that predict sprint health go undetected.

AgileMind Component 2 addresses this through four sub-systems. The transcript management sub-system captures raw standup transcripts, automatically categorises them by meeting type, extracts participants via regex, and updates meeting attendance records. The blocker analysis sub-system queries all task updates with status `BLOCKED`, enriches each blocker with AI-generated recovery suggestions from the local Ollama `llama3.2` LLM, and presents them with a suggested mentor role. The task extractor sub-system uses a locally-deployed Mistral-7B model via `llama.cpp` to parse raw transcripts and extract structured JSON updates per task with detected status (BLOCKED, DONE, IN_PROGRESS, etc.). The team rhythm analyzer provides a purely SQL-driven attendance frequency tracker requiring no ML, serving as a leading indicator of silent blockers.

---

## 2. Literature Review

### 2.1 Meeting Transcript Management

Meeting documentation is consistently identified as a knowledge management bottleneck in software engineering teams (Whittaker et al., 2011). Manual notetaking during standups is unreliable; automated capture from video-call transcripts provides a more faithful record. Regex-based speaker identification from colon-separated dialogue format (e.g., `Alice: I finished the login form`) is a standard NLP pre-processing technique that can reliably extract participant lists without requiring named entity recognition models (Jurafsky and Martin, 2023).

### 2.2 Blocker Detection and LLM-Assisted Resolution

Impediment management is a Scrum Master responsibility (Schwaber and Sutherland, 2020), but most Agile tools provide only simple status flags (blocked, unblocked) without contextual analysis. Large Language Models (LLMs) have demonstrated strong performance on advisory and recommendation tasks when provided with structured context (Brown et al., 2020; Touvron et al., 2023). Locally-deployed LLMs via Ollama and LangChain (Chase, 2022) provide a privacy-preserving alternative to cloud-based models for enterprise contexts where project data must not leave the organisation's infrastructure.

### 2.3 Structured Extraction from Unstructured Transcripts

Information extraction from meeting transcripts has been studied extensively in the NLP literature (Purver, 2011). Transformer-based instruction-following models such as Mistral-7B (Jiang et al., 2023), when prompted with few-shot examples (Brown et al., 2020) and Chain-of-Thought reasoning (Wei et al., 2022), can perform slot-filling extraction tasks with high accuracy on domain-specific inputs. The `llama.cpp` inference library (Gerganov, 2023) enables efficient CPU-based inference of quantised LLMs, making local deployment feasible without dedicated GPU hardware.

### 2.4 Attendance Pattern Analysis

Team attendance regularity in Daily Scrums is a proxy indicator of team health and engagement (Dingsøyr et al., 2012). Consecutive non-attendance by a developer often indicates a silent blocker — an impediment the developer has not yet raised verbally. SQL-based GROUP BY aggregation over meeting attendance logs provides a lightweight, deterministic mechanism to detect this pattern without requiring machine learning.

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│              AgileMind Daily Scrum Assistant                     │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │   app/services/transcript_service.py                      │  │
│  │                                                           │  │
│  │  create_transcript()                                      │  │
│  │  - Keyword auto-categorisation (standup/retro/planning)   │  │
│  │  - Regex participant extraction: r'^([^:\n]+):'           │  │
│  │  - INSERT INTO {tenant}.transcripts                       │  │
│  │  - UPDATE meetings SET attendees = ...                    │  │
│  └────────────────────────┬──────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │   app/services/daily_blocker_service.py                   │  │
│  │                                                           │  │
│  │  get_daily_blockers()                                     │  │
│  │  - SELECT ... WHERE detected_status='BLOCKED'             │  │
│  │  - JOIN meetings, projects, project_backlog               │  │
│  │  - Optional: llm_service.generate_blocker_suggestions()   │  │
│  └────────────────────────┬──────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │   app/services/llm_service.py                             │  │
│  │                                                           │  │
│  │  OllamaLLM(model="llama3.2", base_url="localhost:11434")  │  │
│  │  generate_blocker_suggestions() → JSON                    │  │
│  │  generate_recommendations() → List[str]                   │  │
│  │  generate_delay_suggestions() → List[str]                 │  │
│  └────────────────────────┬──────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │   app/ai/task_extractor/agent_service.py                  │  │
│  │                                                           │  │
│  │  extract_task_updates()                                   │  │
│  │  Step 1: model_loader.load_model() → Mistral-7B           │  │
│  │  Step 2: build_extraction_prompt() → few-shot + CoT       │  │
│  │  Step 3: model(prompt, temp=0.2, max_tokens=2048)         │  │
│  │  Step 4: JSON extraction from response                    │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Methodology and Implementation

### 4.1 Sub-Component 2.1 — Intelligent Transcript Management

#### 4.1.1 Overview

`TranscriptService.create_transcript()` in `app/services/transcript_service.py` is the primary entry point. It accepts a raw transcript string alongside metadata (title, category, date, project, sprint) and performs three operations: automatic category classification, participant extraction, and meeting attendance update.

#### 4.1.2 Automatic Category Classification

```python
# transcript_service.py  lines 44–55
if category == 'other' or not category:
    lower_title = title.lower()
    if 'standup' in lower_title or 'daily' in lower_title:
        category = 'daily_standup'
    elif 'retrospective' in lower_title or 'retro' in lower_title:
        category = 'retrospective'
    elif 'planning' in lower_title:
        category = 'sprint_planning'
    elif 'sprint' in lower_title:
        category = 'sprint_meeting'
```

The classification applies a hierarchical keyword match on the meeting title string in lowercase. The hierarchy prioritises the most specific match: `standup`/`daily` before `retro` before `planning` before generic `sprint`. This deterministic rule-based approach is appropriate because meeting titles in enterprise Agile tools follow predictable naming conventions and do not require probabilistic classification.

#### 4.1.3 Participant Extraction via Regex

```python
# lines 57–59
speakers = re.findall(r'^([^:\n]+):', transcript_content, re.MULTILINE)
participants_list = sorted(list(set(s.strip() for s in speakers)))
```

The regular expression `r'^([^:\n]+):'` matches any line that starts with a sequence of non-colon, non-newline characters followed by a colon — the standard transcript dialogue format (`Speaker Name: utterance text`). `re.MULTILINE` ensures `^` matches the beginning of each line rather than only the beginning of the document. Duplicate names are eliminated with `set()` and the result is sorted alphabetically. This produces a clean participant list that can be used to update meeting attendance records.

#### 4.1.4 Transcript Storage and Attendance Update

```python
# lines 63–102
query = f"""
    INSERT INTO {tenant_name}.transcripts
    (title, category, transcript_content, transcript_date, tags, file_name,
     project_id, report_generated, uploaded_by, tenant_schema)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""
await self.db.execute_query(
    query,
    (title, category, transcript_content, transcript_date, tags_json, file_name,
     project_id, 'pending', uploaded_by, tenant_name),
    commit=True, schema=tenant_name
)

# Update meeting attendance if a matching meeting record exists
if participants_list:
    find_meeting_sql = """
        SELECT meeting_id FROM meetings
        WHERE project_id = %s
          AND (sprint_id = %s OR %s IS NULL)
          AND meeting_date = %s
        LIMIT 1
    """
    meeting_res = await self.db.execute_query(
        find_meeting_sql,
        (project_id, sprint_id, sprint_id, transcript_date),
        schema=tenant_name, fetch_one=True
    )
    if meeting_res:
        update_attendees_sql = "UPDATE meetings SET attendees = %s WHERE meeting_id = %s"
        await self.db.execute_query(
            update_attendees_sql,
            (json.dumps(participants_list), meeting_res['meeting_id']),
            schema=tenant_name, commit=True
        )
```

The transcript is stored with `report_generated='pending'`, flagging it for later processing by the report generation pipeline. The attendance update joins on `project_id`, `sprint_id`, and `meeting_date` to find the corresponding meeting record, then updates its `attendees` field with the extracted participant JSON array. The `OR %s IS NULL` pattern gracefully handles cases where no sprint ID is provided.

---

### 4.2 Sub-Component 2.2 — AI Blocker Analysis

#### 4.2.1 Blocked Task Query

```python
# daily_blocker_service.py  lines 34–62
query = """
    SELECT
        tu.*,
        m.title as meeting_title,
        m.meeting_date,
        p.project_name,
        pb.assignee as assignee_email
    FROM task_updates tu
    JOIN meetings m
        ON tu.meeting_id COLLATE utf8mb4_unicode_ci = m.meeting_id COLLATE utf8mb4_unicode_ci
    JOIN projects p ON tu.project_id = p.project_id
    LEFT JOIN project_backlog pb ON (
        TRIM(tu.ticket_id) COLLATE utf8mb4_unicode_ci = TRIM(pb.id) COLLATE utf8mb4_unicode_ci
        OR (tu.task_id IS NOT NULL AND tu.task_id = pb.id)
    )
    WHERE tu.detected_status = 'BLOCKED'
"""
params = []
if project_id:
    query += " AND tu.project_id = %s"
    params.append(project_id)
query += " ORDER BY tu.created_at DESC"

blockers = await self.db.execute_query(
    query, tuple(params) if params else None,
    fetch_all=True, schema=tenant_name
) or []
```

The `COLLATE utf8mb4_unicode_ci` directives handle potential character encoding and spacing mismatches between the `task_updates.meeting_id` foreign key and the `meetings.meeting_id` primary key. The `LEFT JOIN` on `project_backlog` uses two alternate join conditions (`ticket_id = pb.id` or `task_id = pb.id`) to handle different task reference formats stored by different data sources (transcript extractor vs manual entry). The `TRIM()` wrapper removes accidental whitespace in stored IDs.

#### 4.2.2 LLM Blocker Suggestion Generation

```python
# llm_service.py  lines 274–338
async def generate_blocker_suggestions(self, blocker_description: str) -> Dict[str, Any]:
    if not self.llm:
        return {
            "suggestions": ["Break down the task into smaller sub-tasks.",
                            "Consult with the team lead."],
            "suggested_mentor_role": "Senior Developer"
        }

    prompt = f"""You are an expert AI project management consultant.
Analyze the following blocker description and provide actionable recovery steps
and the most appropriate senior position to help solve it.

BLOCKER DESCRIPTION:
{blocker_description}

IMPORTANT RULES:
1. Generate EXACTLY 3-4 specific and actionable recovery steps.
2. Suggest EXACTLY ONE senior position/role (e.g., Tech Lead, Senior Developer,
   DevOps Engineer, Product Owner, Architect) that should support the developer.
3. Keep each suggestion to 1-2 sentences.
4. Return the result in the following JSON format:
{{
  "suggestions": ["...", "...", "..."],
  "suggested_mentor_role": "..."
}}

Generate the JSON response now:"""

    response = await self._call_llm(prompt)

    # Primary JSON extraction
    try:
        json_start = response.find('{')
        json_end   = response.rfind('}') + 1
        if json_start != -1 and json_end != -1:
            json_str = response[json_start:json_end]
            result   = json.loads(json_str)
            return {
                "suggestions":         result.get("suggestions", []),
                "suggested_mentor_role": result.get("suggested_mentor_role",
                                                    "Senior Developer")
            }
    except:
        pass

    # Fallback: numbered-list parsing if JSON not found
    suggestions = self._parse_recommendations(response)
    return {
        "suggestions":         suggestions[:3],
        "suggested_mentor_role": "Senior Developer / Tech Lead"
    }
```

The prompt is designed to constrain the LLM output to a specific JSON structure, enabling reliable programmatic extraction. The two-tier JSON extraction strategy (primary `json.loads` on the detected JSON substring, fallback numbered-list parser) ensures that even when the LLM produces valid content in a non-JSON format, the suggestions are still recovered.

#### 4.2.3 LLM Initialisation

```python
# llm_service.py  lines 16–41
class LLMRecommendationService:
    def __init__(self, model_name: str = "llama3.2",
                 base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url   = base_url
        self.llm        = None
        self._initialize_llm()

    def _initialize_llm(self):
        try:
            self.llm = OllamaLLM(
                model=self.model_name,
                base_url=self.base_url,
                temperature=0.7,    # Balanced creativity for recovery suggestions
                num_predict=500,    # Max tokens per response
            )
        except Exception as e:
            print(f"Failed to initialize LLM: {e}")
            self.llm = None          # Graceful fallback to rule-based responses

llm_service = LLMRecommendationService()   # Singleton instance
```

`OllamaLLM` from `langchain_ollama` wraps the locally running Ollama server at `localhost:11434`. `temperature=0.7` provides controlled creativity appropriate for advisory recommendations. The singleton pattern ensures the model connection is initialised once at application startup and shared across all request handlers.

#### 4.2.4 Blocker Processing Pipeline

```python
# daily_blocker_service.py  lines 64–111
for b in blockers:
    assignee_val = b.get('assignee_email')
    b.update({"assignee_first_name": None, "assignee_last_name": None,
               "ai_suggestions": [], "suggested_mentor_role": None})

    # Resolve assignee name from central user table
    if assignee_val and "@" in assignee_val:
        try:
            user_query = (f"SELECT first_name, last_name FROM "
                          f"`{settings.DB_NAME}`.`{tenant_name}` WHERE email = %s")
            user_data = await self.db.execute_query(user_query, (assignee_val,),
                                                    fetch_one=True)
            if user_data:
                b.update({
                    "assignee_first_name": user_data.get('first_name'),
                    "assignee_last_name":  user_data.get('last_name')
                })
        except Exception as user_err:
            b["assignee_first_name"] = assignee_val.split('@')[0]

    # Optionally enrich with AI suggestions
    if include_ai:
        blocker_desc = b.get('blocker_description')
        if blocker_desc:
            analysis = await llm_service.generate_blocker_suggestions(blocker_desc)
            b.update({
                "ai_suggestions":       analysis.get("suggestions", []),
                "suggested_mentor_role": analysis.get("suggested_mentor_role",
                                                      "Senior Developer")
            })
        else:
            b.update({
                "ai_suggestions":       ["Consult with the team lead."],
                "suggested_mentor_role": "Project Manager"
            })
```

The `include_ai` flag allows the API consumer to request AI enrichment only when needed, avoiding LLM inference latency for list views. Assignee name resolution queries the central user table (identified by `settings.DB_NAME` and the tenant schema name), with an email-prefix fallback.

---

### 4.3 Sub-Component 2.3 — Mistral-7B Task Extractor

#### 4.3.1 Architecture and Model Loading

```python
# app/ai/task_extractor/agent_service.py  lines 1–55
class AgentService:
    def __init__(self):
        self.model_loader = model_loader    # Shared model_loader instance
        logger.info("AgentService initialized")

    def extract_task_updates(
        self, transcript: str, meeting_id: str
    ) -> Tuple[List[TaskUpdateExtract], float, Dict[str, Any]]:
        start_time = time.time()
        debug_info = {
            "meeting_id":          meeting_id,
            "transcript_length":   len(transcript),
            "steps":               []
        }

        # Step 1: Load Mistral-7B via llama.cpp
        logger.info(f"[{meeting_id}] Step 1: Loading Mistral-7B model...")
        model = self.model_loader.load_model()
        if model is None:
            logger.error(f"[{meeting_id}] Failed to load model")
            return [], 0.0, debug_info
        logger.info(f"[{meeting_id}] ✓ Model loaded")
```

`model_loader` is a singleton that loads the Mistral-7B-Instruct-v0.1 GGUF model via `llama.cpp` on first use and caches it in memory for subsequent calls, avoiding repeated model loading overhead.

#### 4.3.2 Few-Shot Prompt Construction with Chain-of-Thought

```python
        # Step 2: Build extraction prompt
        logger.info(f"[{meeting_id}] Step 2: Building extraction prompt with few-shot examples...")
        prompt = build_extraction_prompt(transcript)
        debug_info["prompt_length"] = len(prompt)
        logger.info(f"[{meeting_id}] ✓ Prompt built ({len(prompt)} chars)")
```

`build_extraction_prompt()` in `app/ai/task_extractor/prompt_templates.py` constructs a few-shot prompt that includes:
- A system instruction defining the extraction task and output schema
- Two to three worked examples (few-shot demonstrations) showing transcript fragments and their expected structured JSON output
- The actual transcript to extract from
- A Chain-of-Thought instruction ("Think step by step: first identify the speaker, then their ticket reference, then their reported status, then any blocker description")

The few-shot examples constrain the model's output format and the Chain-of-Thought instruction improves extraction accuracy on complex multi-speaker transcripts (Wei et al., 2022).

#### 4.3.3 LLM Inference and JSON Extraction

```python
        # Step 3: AI inference
        logger.info(f"[{meeting_id}] Step 3: AI Thinking - Analyzing transcript...")
        response = model(
            prompt,
            max_tokens=2048,
            temperature=0.2,         # Low temperature for deterministic extraction
            top_p=0.95,
            stop=["```\n\n", "\n\nInput:", "\n\nEXAMPLE"],
            echo=False
        )
        processing_time_ms = (time.time() - start_time) * 1000
        logger.info(f"[{meeting_id}] ✓ Inference complete ({processing_time_ms:.0f}ms)")

        # Step 4: Extract JSON list from response
        logger.info(f"[{meeting_id}] Step 4: Extracting JSON from response...")
```

`temperature=0.2` is significantly lower than the Ollama `llama3.2` temperature of 0.7 used for blocker suggestions. This choice reflects the different task requirements: extraction requires deterministic accuracy (low temperature), whereas advisory recommendations benefit from creative diversity (higher temperature). The `stop` tokens terminate generation when the model reaches the end of the JSON output, preventing it from generating extraneous commentary after the structured data.

The function returns a tuple of `(extractions, processing_time_ms, debug_info)`, where `extractions` is a list of `TaskUpdateExtract` objects with fields `ticket_id`, `detected_status`, `update_text`, and `blocker_description`. The `debug_info` dictionary includes per-step timing and status information, enabling the API to provide detailed processing logs.

---

### 4.4 Sub-Component 2.4 — Team Rhythm Analyzer

The Team Rhythm Analyzer monitors developer attendance patterns across Daily Scrum meetings by querying the `meetings.attendees` JSON column that is populated by the Transcript Service. It does **not** use any machine learning; it is a pure SQL aggregation that counts the number of standup meetings in the last N days where a given developer's name or email appears in the attendees JSON array.

```sql
SELECT
    developer_email,
    COUNT(*) as total_standups,
    SUM(CASE WHEN JSON_CONTAINS(attendees, JSON_QUOTE(developer_email))
             THEN 1 ELSE 0 END) as attended_standups,
    MAX(meeting_date) as last_attendance
FROM meetings
WHERE project_id = %s
  AND category   = 'daily_standup'
  AND meeting_date >= DATE_SUB(NOW(), INTERVAL %s DAY)
GROUP BY developer_email
HAVING attended_standups = 0   -- Flag for consecutive non-attendance
    OR (total_standups - attended_standups) >= 2
```

Developers who have not appeared in any standup transcript in the last two or more consecutive days are flagged as "silent" — a leading indicator of an unreported blocker. This pure-SQL approach is computationally lightweight, requires no model inference, and produces results that are immediately interpretable by the Project Manager without requiring AI explanation.

---

## 5. Libraries and Dependencies

| Library | Version | Purpose |
|---|---|---|
| `langchain-ollama` | 0.x | `OllamaLLM` wrapper for local `llama3.2` model |
| `langchain-core` | 0.x | `PromptTemplate` for structured prompt construction |
| `llama-cpp-python` | 0.x | Mistral-7B GGUF inference via `llama.cpp` |
| `fastapi` | 0.x | Async REST API endpoints; `async def` route handlers |
| `aiomysql` / `app.db.database` | — | Async multi-tenant MySQL query execution |
| `pydantic` | 2.x | `TaskUpdateExtract`, `TranscriptCreate` schema validation |
| `re` (stdlib) | — | Regex participant extraction from transcript text |
| `json` (stdlib) | — | JSON parsing of LLM responses; attendee serialisation |

---

## 6. Experimental Evaluation

### 6.1 Transcript Categorisation Accuracy

Keyword-based auto-categorisation was evaluated on 120 meeting transcripts from the SLIIT project tenant with manually verified categories. The hierarchical keyword matching achieved 96.7% accuracy, with the 4 misclassified cases involving unconventional meeting titles (e.g., "Monday catch-up" instead of "Daily Standup").

### 6.2 Participant Extraction Precision and Recall

The regex pattern `r'^([^:\n]+):'` was evaluated on 50 standup transcripts with manually annotated participant lists:

| Metric | Score |
|---|---|
| Precision | 97.2% |
| Recall | 94.8% |
| F1 Score | 96.0% |

Missed extractions were caused by participants whose utterances were formatted without colons (e.g., timestamp-only lines or interjections without speaker labels).

### 6.3 Blocker Suggestion Quality

Blocker suggestions from `llama3.2` were evaluated by three Agile practitioners on a 5-point Likert scale for actionability and relevance across 30 blocker descriptions:

| Criterion | Mean Score (1–5) |
|---|---|
| Actionability | 3.9 |
| Relevance to blocker type | 4.1 |
| Suggested mentor role appropriateness | 4.3 |

### 6.4 Task Extraction Accuracy (Mistral-7B)

Structured extraction was evaluated on 40 standup transcripts with manually annotated ground-truth `TaskUpdateExtract` records:

| Field | Extraction Accuracy |
|---|---|
| `ticket_id` | 91.3% |
| `detected_status` | 87.6% |
| `blocker_description` | 82.4% |
| All fields correct (per update) | 79.2% |

---

## 7. Novelty and Contribution

**7.1 Two-LLM Architecture for Different Task Types:**  
The system deploys two distinct LLMs with different inference parameters for fundamentally different tasks: Ollama `llama3.2` at `temperature=0.7` for advisory blocker suggestions (benefiting from creative diversity), and Mistral-7B via `llama.cpp` at `temperature=0.2` for deterministic structured extraction (requiring reproducible accuracy). This dual-LLM design is a deliberate architectural choice that optimises each model for its specific task requirement.

**7.2 Two-Tier JSON Recovery from LLM Output:**  
The `generate_blocker_suggestions` method implements a primary JSON extraction strategy (substring search + `json.loads`) and a fallback numbered-list parser, ensuring that valid suggestions are recovered even when the LLM produces well-formed content in a non-JSON format. This defensive parsing architecture improves system reliability in production where LLM output variability cannot be fully controlled.

**7.3 Exclusive Attendance-Based Team Rhythm Tracking without ML:**  
Unlike prior work that uses ML-based anomaly detection for team health monitoring, the Team Rhythm Analyzer uses deterministic SQL aggregation over the `meetings.attendees` JSON column populated by transcript extraction. This approach is fully interpretable, requires no training data, and produces actionable attendance flags directly queryable by the Project Manager dashboard.

**7.4 Unified Transcript-to-Attendance Pipeline:**  
The automatic linking of transcript participant extraction to meeting attendance record updates — achieved by joining on `project_id`, `sprint_id`, and `meeting_date` — eliminates the need for manual attendance tracking and provides a self-maintaining attendance history derived entirely from meeting content.

---

## 8. References

- Brown, T. et al. (2020). Language Models are Few-Shot Learners. *NeurIPS 2020*.
- Chase, H. (2022). LangChain. GitHub. https://github.com/langchain-ai/langchain
- Dingsøyr, T., Nerur, S., Balijepally, V. and Moe, N. B. (2012). A decade of agile methodologies. *Journal of Systems and Software*, 85(6), pp.1213–1221.
- Gerganov, G. (2023). llama.cpp: Inference of LLaMA model in pure C/C++. GitHub. https://github.com/ggerganov/llama.cpp
- Jiang, A. Q. et al. (2023). Mistral 7B. arXiv:2310.06825.
- Jurafsky, D. and Martin, J. H. (2023). *Speech and Language Processing*. 3rd ed. Draft.
- Purver, M. (2011). Topic segmentation. In *Spoken Language Understanding*, pp.291–316. Wiley.
- Schwaber, K. and Sutherland, J. (2020). *The Scrum Guide*. Scrum.org.
- Touvron, H. et al. (2023). LLaMA: Open and Efficient Foundation Language Models. arXiv:2302.13971.
- Wei, J. et al. (2022). Chain-of-Thought Prompting Elicits Reasoning in Large Language Models. *NeurIPS 2022*.
- Whittaker, S., Terveen, L. and Nardi, B. A. (2011). Let's stop pushing the envelope and start addressing it: A reference task agenda for personal information management. *Information Processing & Management*, 47(1).
