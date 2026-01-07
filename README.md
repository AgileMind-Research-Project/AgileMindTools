# AgileMindTools

**AI-Powered Agile Project Management Suite**

A collection of AWS Lambda functions designed to automate and optimize agile project management workflows using AI/ML techniques, NLP, and intelligent algorithms. This suite integrates with Jira to provide automated task assignment, backlog prioritization, task splitting, and project management capabilities.

---

## 📁 Project Structure

```
AgileMindTools/
├── Assign_Tasks/          # Intelligent task assignment module
├── Backlog_Prioritize/    # AI-based backlog prioritization
├── Get_All_Tenants/       # Multi-tenant database management
├── Get_Backlog/           # Jira synchronization module
└── Task_Split/            # Automated task decomposition
```

---

## 🚀 Modules Overview

### 1. **Assign_Tasks** - Intelligent Task Assignment
*Location: `Assign_Tasks/assignee.py`*

Automatically assigns tasks to developers based on skills, experience, workload, and work history using intelligent matching algorithms.

#### Key Functions:
- **`get_developers(tenant, project)`** - Fetches active developers from database
- **`fetch_developers_from_db(tenant, project)`** - Retrieves user details with stack, technologies, and experience
- **`get_developer_by_email(tenant, project, email)`** - Retrieves specific developer information
- **`get_all_project(tenant)`** - Fetches all projects for a tenant
- **`get_unassigned_parent_tasks(project_id, tenant)`** - Gets backlog items without sprint assignment
- **`get_subtasks_by_parent_ids(parent_ids, tenant_db)`** - Retrieves subtasks for parent task IDs
- **`assign_tasks_to_developers(project_id, tenant_table, tenant_db)`** - Main assignment algorithm using skill matching, stack matching, experience scoring, and workload balancing

#### Features:
- ✅ Skill-based task matching
- ✅ Technology stack alignment (backend/frontend)
- ✅ Experience-weighted scoring
- ✅ Workload balancing
- ✅ Work history analysis
- ✅ Multi-project support

---

### 2. **Backlog_Prioritize** - AI-Powered Backlog Prioritization
*Location: `Backlog_Prioritize/Backlog_prioritize.py`*

Uses machine learning and NLP to intelligently prioritize backlog items based on historical data, semantic analysis, and business value.

#### Key Functions:
- **`train_and_prioritize(historical_csv_path, backlog_items, additional_historical_df)`** - Main training and prioritization engine

#### AI/ML Techniques:
1. **Semantic Embeddings** - Uses SentenceTransformer ('all-MiniLM-L6-v2') for text analysis
2. **PCA (Principal Component Analysis)** - Dimensionality reduction to 3 components
3. **Linear Regression** - Learns coefficients from historical completion data
4. **KMeans Clustering** - Automatic MoSCoW categorization (Must/Should/Could/Won't Have)
5. **WSJF Calculation** - Weighted Shortest Job First prioritization

#### Prioritization Factors:
- 📊 **AI Semantic Scores** - Text similarity analysis
- 🎯 **Priority Weights** - High/Medium/Low priority mapping
- 🔴 **Severity Weights** - Blocker/Critical/Major/Minor/Trivial
- 🐛 **Bug Boost** - Automatic elevation of critical bugs
- 📈 **User Value** - Calculated from AI scores and weights
- ⏰ **Time Criticality** - Urgency factor
- 🛡️ **Risk Reduction** - Risk mitigation scoring
- 💰 **Cost of Delay** - Combined business value metric

#### Output:
- `prioritized_backlog_ai.csv` - Prioritized backlog with WSJF scores
- `prioritization_report_ai.txt` - Detailed prioritization report

---

### 3. **Get_All_Tenants** - Multi-Tenant Management
*Location: `Get_All_Tenants/get_tenants.py`*

Manages multi-tenant database architecture by retrieving tenant table lists from MySQL database.

#### Key Functions:
- **`get_all_tables(exclude_system_tables=True)`** - Retrieves all tenant tables from database
- **`lambda_handler(event, context)`** - AWS Lambda entry point

#### Features:
- ✅ Automatic system table exclusion (roles, password_reset_tokens)
- ✅ RESTful API response format
- ✅ CORS support
- ✅ Error handling and logging

#### Response Format:
```json
{
  "statusCode": 200,
  "body": ["tenant1", "tenant2", "tenant3"]
}
```

---

### 4. **Get_Backlog** - Jira Synchronization
*Location: `Get_Backlog/get_backlogData.py`*

Synchronizes Jira backlog data with MySQL database, supporting real-time updates and historical tracking.

#### Key Functions:
- **`get_all_project(tenant)`** - Fetches all projects from database
- **`get_jira_credentials(tenant)`** - Retrieves Jira API credentials from AWS Secrets Manager
- **`fetch_jira_backlog(jira_url, email, api_token, project_key)`** - Fetches issues from Jira Cloud API
- **`transform_jira_issue(issue, project_id)`** - Transforms Jira issue format to database schema
- **`sync_jira_backlog(tenant)`** - Main synchronization function
- **`lambda_handler(event, context)`** - Lambda entry point with multiple actions

#### Supported Actions:
1. **`get_projects`** - Get list of all projects
2. **`sync_backlog`** - Sync Jira backlog to database

#### Field Mappings:
- **Issue Types**: Story, Feature, Bug, Change (mapped from Jira)
- **Status**: Todo, In Progress, Done
- **Priority**: High, Medium, Low
- **Severity**: Blocker, Critical, Major, Minor, Trivial
- **Custom Fields**: Story Points, Start Date, Severity

#### Features:
- ✅ Atlassian Cloud API integration
- ✅ Automatic field mapping and transformation
- ✅ Batch synchronization
- ✅ Deleted item tracking
- ✅ Historical data preservation
- ✅ AWS Secrets Manager integration

---

### 5. **Task_Split** - Intelligent Task Decomposition
*Location: `Task_Split/split_task.py`*

Uses NLP and linguistic analysis to automatically split complex tasks into manageable subtasks with dynamic tag detection.

#### Key Functions:
- **`get_all_project(tenant)`** - Retrieves project list
- **`get_backlog_details_with_priority(project_id, tenant)`** - Gets prioritized backlog items
- **`get_dynamic_keywords(project_id, tenant)`** - Extracts nouns and verbs from project context
- **`build_tag_keyword_map(project_tasks)`** - Dynamically discovers tag categories using NLP
- **`detect_task_tags(text, tag_indicators)`** - Uses NLP to determine relevant tags
- **`extract_subtasks_advanced(summary, description, dynamic_nouns, dynamic_verbs)`** - Extracts subtasks using linguistic patterns
- **`generate_subtask_description(parent_task, sub_summary, tags)`** - Generates natural subtask descriptions
- **`split_backlog_tasks(project_id, tenant)`** - Main orchestration function

#### NLP Features:
- 🧠 **spaCy Integration** - Advanced linguistic analysis (en_core_web_sm)
- 🏷️ **Dynamic Tag Detection** - Automatic categorization (backend, frontend, qa, testing, devops, etc.)
- 📝 **Noun Chunk Extraction** - Identifies key entities
- 🎯 **Verb Lemmatization** - Action identification
- 🔗 **Dependency Detection** - Sequential task identification
- 📊 **Story Point Distribution** - Automatic effort allocation

#### Tag Categories (Auto-detected):
- Backend
- Frontend
- QA/Testing
- DevOps
- Documentation
- Database
- API
- Security
- UI

#### Subtask Creation Logic:
1. Extract verbs and nouns from parent task
2. Generate subtask phrases (verb + noun combinations)
3. Calculate complexity and story points
4. Detect dependencies
5. Assign dynamic tags using NLP
6. Distribute parent story points among subtasks

---

## 🛠️ Technology Stack

### Core Technologies:
- **Python 3.12**
- **AWS Lambda** - Serverless compute
- **MySQL** - Relational database
- **Jira Cloud API** - Issue tracking integration

### AI/ML Libraries:
- **sentence-transformers** - Semantic text embeddings
- **scikit-learn** - Machine learning algorithms
- **spaCy** - Natural language processing
- **numpy/pandas** - Data manipulation

### Integration Libraries:
- **atlassian-python-api** - Jira Cloud integration
- **boto3** - AWS services (Secrets Manager)
- **SQLAlchemy** - Database ORM

---

## 📦 Installation

### Prerequisites:
- Python 3.12+
- MySQL Database
- AWS Account (for Lambda deployment)
- Jira Cloud instance

### Setup:

1. **Clone the repository:**
```bash
git clone <repository-url>
cd AgileMindTools
```

2. **Install dependencies for each module:**
```bash
# Assign Tasks
cd Assign_Tasks
python -m venv env
env\Scripts\activate  # Windows
source env/bin/activate  # Linux/Mac
pip install -r requirements.txt

# Repeat for other modules
cd ../Backlog_Prioritize
pip install -r requirements.txt

cd ../Get_Backlog
pip install -r requirements.txt

cd ../Task_Split
pip install -r requirements.txt
```

3. **Download spaCy model:**
```bash
python -m spacy download en_core_web_sm
```

4. **Configure environment variables:**
Create `.env` or set environment variables for:
- `DB_HOST` - MySQL host
- `DB_NAME` - Database name
- `DB_USER` - Database user
- `DB_PASSWORD` - Database password
- AWS credentials for Secrets Manager

5. **Set up AWS Secrets Manager:**
Store Jira API tokens with tenant-specific keys

---

## 🚦 Usage

### Local Testing:

#### 1. Assign Tasks:
```bash
cd Assign_Tasks
python assignee.py
```

#### 2. Prioritize Backlog:
```bash
cd Backlog_Prioritize
python Backlog_prioritize.py
```

#### 3. Get Tenants:
```bash
cd Get_All_Tenants
python get_tenants.py
```

#### 4. Sync Jira Backlog:
```bash
cd Get_Backlog
python get_backlogData.py
```

#### 5. Split Tasks:
```bash
cd Task_Split
python split_task.py
```

### AWS Lambda Deployment:

Each module includes a `lambda_handler` function for AWS Lambda deployment:

```python
def lambda_handler(event, context):
    # Lambda entry point
    pass
```

**Event Formats:**

**Get Backlog:**
```json
{
  "tenant": "sliit",
  "action": "sync_backlog"
}
```

**Get Tenants:**
```json
{}
```

**Task Assignment:**
```json
{
  "project_id": 10237,
  "tenant": "sliit"
}
```

---

## 📊 Database Schema

### Required Tables:

1. **`projects`** - Project information
2. **`<tenant_name>`** - User/developer information with JSON projects field
3. **`jira_integrations`** - Jira connection details
4. **`project_backlog`** - Main backlog items
5. **`project_backlog_priority`** - Priority rankings
6. **`roles`** - User roles (system table)
7. **`password_reset_tokens`** - Auth tokens (system table)

---

## 🔐 Security

- ✅ AWS Secrets Manager for credential storage
- ✅ Parameterized SQL queries (SQLAlchemy)
- ✅ CORS configuration
- ✅ Environment variable management
- ✅ Tenant isolation

---

## 📈 Key Algorithms

### 1. WSJF (Weighted Shortest Job First):
```
WSJF = Cost of Delay / Story Points
Cost of Delay = User Value + Time Criticality + Risk Reduction
```

### 2. Task Assignment Score:
```
Score = Technology Match × 10 + Stack Match × 5 + Experience + Work History × 3 - Workload × 0.5
```

### 3. MoSCoW Categorization:
- Automatic clustering using KMeans (4 clusters)
- Bug override logic for critical issues
- WSJF-based cluster ranking

---

## 🧪 Testing

Each module includes local testing functionality in the `if __name__ == "__main__"` block.

Run tests:
```bash
python <module_file>.py
```

---

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

---

## 📄 License

[Specify your license here]

---

## 👥 Authors

[Your team/organization name]

---

## 📞 Support

For issues and questions:
- Create an issue in the repository
- Contact: [your-email@example.com]

---

## 🔄 Version History

- **v1.0** - Initial release with 5 core modules

---

## 🎯 Future Enhancements

- [ ] Real-time notification system
- [ ] Enhanced ML models for better predictions
- [ ] Sprint planning automation
- [ ] Velocity tracking and forecasting
- [ ] Integration with additional project management tools
- [ ] Dashboard and visualization components

---

**Built with ❤️ for Agile Teams**
