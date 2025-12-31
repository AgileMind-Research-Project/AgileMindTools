# Jira Backlog Data Sync Module

This module fetches backlog items from Jira and stores them in the MySQL `project_backlog` table.

## Overview

The module connects to Jira using API credentials stored in AWS Secrets Manager, retrieves backlog items for each project, and synchronizes them with your MySQL database.

## Features

- 🔐 Secure credential management via AWS Secrets Manager
- 📊 Fetches all backlog items from Jira
- 🔄 Automatic data transformation to match database schema
- 📝 Maps Jira issue types, statuses, and priorities to your schema
- 💾 Bulk insert/update of backlog items
- 🌐 Support for multiple projects
- 🔍 Handles Atlassian Document Format (ADF) for descriptions

## Database Schema

The `project_backlog` table structure:

| Column | Type | Description |
|--------|------|-------------|
| id | bigint | Auto-increment primary key |
| project_id | bigint | Project ID (FK to projects table) |
| summary | varchar(255) | Issue summary/title |
| description | text | Detailed description |
| issue_type | varchar(100) | Type: story, feature, change, bug |
| status | varchar(100) | Status: todo, in_progress, done |
| priority | varchar(100) | Priority: high, medium, low |
| assignee | varchar(255) | Assigned person |
| created_at | datetime | Creation timestamp |
| updated_at | datetime | Last update timestamp |

## Jira to Database Mapping

### Issue Types

| Jira Type | Database Type |
|-----------|---------------|
| Story, User Story | story |
| Feature, New Feature, Epic | feature |
| Bug, Defect | bug |
| Change, Improvement, Task | change |

### Statuses

| Jira Status | Database Status |
|-------------|-----------------|
| Backlog, To Do, Open | todo |
| In Progress, In Development | in_progress |
| Done, Closed, Resolved, Complete | done |

### Priorities

| Jira Priority | Database Priority |
|---------------|-------------------|
| Highest, Critical | high |
| High, Major | high |
| Medium | medium |
| Low, Minor, Trivial | low |
| Lowest | low |

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file with your MySQL database credentials:

```env
DB_HOST=your_mysql_host
DB_PORT=your_mysql_port
DB_NAME=agilemind_db
DB_USER=your_db_user
DB_PASSWORD=your_db_password
AWS_REGION=ap-southeast-1
```

### 3. Configure Jira Integration

#### Database Setup

The Jira URL and email are stored in the `jira_integrations` table:

```sql
CREATE TABLE `jira_integrations` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `jira_url` varchar(255) NOT NULL COMMENT 'Base URL of Jira instance',
  `email` varchar(255) NOT NULL COMMENT 'Jira account email',
  `api_token` tinyint(1) DEFAULT '0' COMMENT 'Whether token is validated and active',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_jira_account` (`jira_url`,`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

Insert your Jira integration details:

```sql
INSERT INTO jira_integrations (jira_url, email, api_token)
VALUES ('https://your-domain.atlassian.net', 'your-email@example.com', 1);
```

#### AWS Secrets Manager Setup

The API token is stored securely in AWS Secrets Manager with the naming pattern:

```
tenant_{tenant_name}_jira_api_token
```

The secret value can be either:

**Option 1: JSON object**
```json
{
  "api_token": "your-api-token-here"
}
```

**Option 2: Plain string**
```
your-api-token-here
```

### 4. How Credentials Are Retrieved

The system uses a hybrid approach for security:

1. **Jira URL and Email**: Retrieved from `jira_integrations` table in MySQL
2. **API Token**: Retrieved from AWS Secrets Manager using `get_credential(tenant)`

This approach:
- ✅ Keeps sensitive API tokens in secure AWS Secrets Manager
- ✅ Allows easy management of Jira URLs and emails in the database
- ✅ Maintains separation of concerns

## Usage

### As a Lambda Function

#### Get All Projects

```python
event = {
    "tenant": "sliit",
    "action": "get_projects"
}
result = lambda_handler(event, None)
```

Response:
```json
[
  {
    "project_id": 10204,
    "project_name": "AgileMInd_New",
    "key": "AMNT"
  },
  {
    "project_id": 10237,
    "project_name": "Test AM",
    "key": "TAM"
  }
]
```

#### Sync Jira Backlog

```python
event = {
    "tenant": "sliit",
    "action": "sync_backlog"
}
result = lambda_handler(event, None)
```

Response:
```json
{
  "success": true,
  "projects_synced": 3,
  "items_synced": 45
}
```

### Local Testing

Run the script directly:

```bash
python get_backlogData.py
```

This will:
1. Get all projects for the "sliit" tenant
2. Sync all Jira backlog items to the database

## Functions

### Main Functions

- **`sync_jira_backlog(tenant)`** - Main function to sync all Jira backlog data
- **`get_all_project(tenant)`** - Retrieve all projects from database
- **`get_jira_credentials(tenant)`** - Get Jira API credentials from AWS Secrets Manager
- **`fetch_jira_backlog(jira_url, email, api_token, project_key)`** - Fetch backlog from Jira API
- **`transform_jira_issue(issue, project_id)`** - Transform Jira issue to database format
- **`insert_backlog_items(backlog_items, tenant)`** - Insert/update items in database

### Helper Functions

- **`extract_text_from_adf(adf_content)`** - Extract plain text from Atlassian Document Format

## JQL Query

The module uses the following JQL to fetch backlog items:

```jql
project = {project_key} AND (sprint is EMPTY OR status in (Backlog, 'To Do', TODO)) ORDER BY created DESC
```

You can customize this in the `fetch_jira_backlog()` function to match your Jira workflow.

## Error Handling

The module includes comprehensive error handling:
- Logs all errors with detailed messages
- Continues processing other projects if one fails
- Returns success/failure status for each operation
- Validates credentials and configuration

## Logging

All operations are logged using Python's logging module. Key events logged:
- Credential retrieval
- Project fetching
- Jira API calls
- Data transformation
- Database operations
- Errors and warnings

## Notes

- The module fetches up to 100 issues per API call (pagination handled automatically)
- Existing backlog items with the same data will be updated (upsert behavior)
- Descriptions in Atlassian Document Format are converted to plain text
- Timezone information from Jira timestamps is preserved during conversion

## Troubleshooting

### No Credentials Found
- Check AWS Secrets Manager for the correct secret name pattern
- Verify AWS credentials are configured
- Ensure the tenant name matches the secret name

### Database Connection Error
- Verify `.env` file configuration
- Check database host and port accessibility
- Validate database user permissions

### Jira API Errors
- Verify Jira URL is correct (include https://)
- Check API token is valid and not expired
- Ensure user has permission to access projects

## Example Output

```
=== Getting all projects ===
[
  {
    "project_id": 10204,
    "project_name": "AgileMInd_New",
    "key": "AMNT"
  },
  {
    "project_id": 10237,
    "project_name": "Test AM",
    "key": "TAM"
  },
  {
    "project_id": 10270,
    "project_name": "New Project Test",
    "key": "NPTM"
  }
]

=== Syncing Jira backlog ===
INFO: Successfully retrieved Jira credentials for tenant: sliit
INFO: Syncing backlog for project: New Project Test (NPTM)
INFO: Fetching issues for project NPTM with JQL: project = "NPTM" ORDER BY created DESC
INFO: Fetched 2 backlog items for project NPTM
INFO: Successfully inserted/updated 2 backlog items
INFO: Synced 2 items for project New Project Test
{
  "success": true,
  "projects_synced": 3,
  "items_synced": 2
}
```

### Sample Inserted Data

The module successfully extracts and stores:
- **Summary**: Issue title/name
- **Description**: Full description from Jira
- **Issue Type**: Mapped to story/feature/bug/change
- **Status**: Mapped to todo/in_progress/done
- **Priority**: Mapped to high/medium/low
- **Assignee**: Display name of assigned user
- **Labels/Tags**: Stored within description as JSON array (e.g., `[TAGS: ["auth", "chat"]]`)
- **Timestamps**: Created and updated dates

## Technical Details

- **Library**: Uses `atlassian-python-api` v4.0.7+ for reliable Jira Cloud API v3 support
- **Authentication**: Combines database-stored URL/email with AWS Secrets Manager API tokens
- **Pagination**: Automatic handling of large result sets
- **Error Handling**: Graceful failures with detailed logging
- **Data Mapping**: Intelligent transformation of Jira fields to database schema

## Important Notes

### Labels/Tags Storage

Currently, labels are appended to the description field as JSON since the current schema doesn't have a dedicated tags column. Format: `[TAGS: ["tag1", "tag2"]]`

**Recommendation**: Consider adding a `tags` column (JSON or TEXT type) to the `project_backlog` table for better data structure:

```sql
ALTER TABLE project_backlog ADD COLUMN tags JSON COMMENT 'Issue labels/tags from Jira';
```
