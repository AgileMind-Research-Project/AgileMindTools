# Notification Debugging Guide

## Problem
Data is being stored in the database, but notifications are not being created for project managers.

## Possible Causes

### 1. **API URL Not Configured**
- The script needs to know where your API server is running
- Default: `http://localhost:8000`
- **Fix**: Set environment variable before running:
  ```bash
  # Windows PowerShell
  $env:API_URL = "http://localhost:8000"
  python prioritize_upcoming_sprints.py
  
  # Windows CMD
  set API_URL=http://localhost:8000
  python prioritize_upcoming_sprints.py
  
  # Linux/Mac
  export API_URL=http://localhost:8000
  python prioritize_upcoming_sprints.py
  ```

### 2. **API Server Not Running**
- The backend API must be running to receive notification requests
- **Check**: Visit `http://localhost:8000/health` in browser
- **Fix**: Start the API server:
  ```bash
  cd d:\Research\AjileMindApi
  python main.py
  ```

### 3. **No Project Managers Assigned**
- The project's `project_manager` field might be NULL or empty
- **Check**: Query the database:
  ```sql
  SELECT project_id, project_name, project_manager 
  FROM projects 
  WHERE project_id = 10270;
  ```
- **Fix**: Assign project managers in the project creation/edit form

### 4. **Network/Firewall Issues**
- Firewall might be blocking local HTTP requests
- **Check**: Temporarily disable firewall for testing

### 5. **Port Already in Use**
- API might not be running on port 8000
- **Check**: See what port your API is using in the terminal
- **Fix**: Update API_URL to match

## How to Debug

### Step 1: Run the Test Script
```bash
cd d:\Research\AgileMindTools\Backlog_Prioritize
python test_notification.py
```

This will show you:
- ✅ If the project exists
- ✅ If project_manager field has values
- ✅ What API URL is being used
- ✅ If the API is reachable
- ✅ Detailed notification creation logs

### Step 2: Check the Logs
When you run `prioritize_upcoming_sprints.py`, look for these log messages:

```
[NOTIFICATION] Starting notification creation for project 10270
[NOTIFICATION] Querying project details from database
[NOTIFICATION] Project name: YourProject
[NOTIFICATION] Project manager raw value: ["manager@example.com"]
[NOTIFICATION] Parsed project_manager from JSON string: ['manager@example.com']
[NOTIFICATION] Using API URL: http://localhost:8000
[NOTIFICATION] Notification payload: {...}
[NOTIFICATION] Sending POST request to http://localhost:8000/api/v1/notifications
[NOTIFICATION] Response status code: 200
[NOTIFICATION] Response body: {...}
✅ [NOTIFICATION] Successfully sent notification
```

### Step 3: Common Log Messages

#### ⚠️ "No project managers assigned"
```
[NOTIFICATION] No project managers assigned to project 10270, skipping notification
```
**Fix**: Add project managers to the project in the UI

#### ⚠️ "project_manager field is NULL"
```
[NOTIFICATION] project_manager field is NULL or empty
```
**Fix**: Edit the project and assign project managers

#### ❌ "Cannot reach API"
```
❌ Cannot reach API: ConnectionRefusedError
```
**Fix**: Start the backend API server

#### ❌ "Response status code: 500"
```
[NOTIFICATION] Response status code: 500
[NOTIFICATION] Response body: {"detail": "..."}
```
**Fix**: Check API server logs for errors

## Quick Fix Checklist

1. ✅ Is the backend API running? (`python main.py` in AjileMindApi folder)
2. ✅ Can you access http://localhost:8000/health?
3. ✅ Does the project have project_manager assigned?
4. ✅ Is API_URL environment variable set correctly?
5. ✅ Are you running the latest version of the code?

## Manual Test

You can manually test the notification API:

```bash
# Test with curl (Windows PowerShell)
curl -X POST http://localhost:8000/api/v1/notifications `
  -H "Content-Type: application/json" `
  -d '{
    "tenant_name": "sliit",
    "header": "Test Notification",
    "description": "This is a test notification",
    "related_users": ["your.email@example.com"],
    "notification_type": "INFO"
  }'
```

If this works, you should see the notification in the UI at `/dashboard/notifications`

## Still Not Working?

Run the prioritization script and paste the full console output showing all `[NOTIFICATION]` log messages.
