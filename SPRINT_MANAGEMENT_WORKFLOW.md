# 🏁 AI-Lifecycle: The Complete Sprint Management Workflow

Welcome to the **AgileMindTools Sprint Management Guide**! This document explains how our AI suite orchestrates the entire lifecycle of a sprint—from the first planning meeting to the final review.

---

## 🌟 The Vision: A Seamless Sprint Lifecycle
Managing a sprint involves many moving parts: meetings, documentation, updates, and task tracking. Our AI simplifies this by automating the data-entry work, allowing your team to focus on building great software.

---

## 📅 Phase 1: Sprint Planning (From Voice to Jira)

### 1. Transcript Analysis (The LLM Brain)
At the start of your sprint, you simply record your **Sprint Planning Meeting**. The system uses an **LLM (Large Language Model)** to "listen" to the transcript.
*   **Task Extraction**: It identifies every "To-Do" item mentioned in the meeting.
*   **Effort Estimation**: It listens for discussions about complexity and suggests **Story Points** (Effort).
*   **Assignee Identification**: It notes who volunteered for or was assigned to each task.

### 2. Human-in-the-Loop (Verification)
The AI provides a draft list. A human (Project Manager or Team Lead) reviews the suggestions in the dashboard to ensure the AI didn't miss a detail. One click verifies the data.

### 3. Jira Integration (Automatic Creation)
Once verified, the system automatically:
*   Creates all tasks and subtasks in **Jira**.
*   Sets the correct assignees and story points.
*   **Starts the Sprint** in the Jira system.

---

## 📄 Phase 2: Automated Documentation

The system automatically generates two critical documents to keep everyone aligned:

### 1. Sprint Planning Document
Generated immediately after the sprint starts, this doc includes:
*   **Sprint Goals**: What we aim to achieve.
*   **The Commitment**: A full list of tasks and who is responsible for them.
*   **Capacity Overview**: A summary of the total story points committed for the period.

### 2. Next Sprint Timeline (Smart Scheduling)
The system calculates the **Next Sprint Start Date** based on your team's historical velocity and the current sprint's performance. It ensures a consistent "rhythm" for your team.

---

## 📢 Phase 3: Team Communication

All updates are pushed to your **Project Channel** (e.g., Slack or Microsoft Teams).
*   **Sprint Start Alerts**: Notifies the team that the sprint is live.
*   **Daily Syncs**: Keeps the channel updated with current progress.

---

## 🔄 Phase 4: Sprint Review & Cleanup

At the end of the sprint, the "Cycle of Intelligence" completes:

### 1. Review Comparison
The AI compares your **Sprint Review Meeting transcript** against the original **Sprint Planning Document**. 
*   **Completion Check**: It identifies what was finished and what wasn't.
*   **Status Updates**: It automatically updates the Jira statuses based on the discussion.

### 2. Incomplete Task Handling (The Carryover)
If a task wasn't finished, the system won't let it fall through the cracks.
*   **Automatic Carryover**: Incomplete tasks are logically reassigned to the **Next Sprint**.
*   **History Update**: The AI records *why* it wasn't finished (e.g., "Blocked" or "Estimate too low") to improve next week's prioritization.

---

## 📈 Why This Comprehensive Workflow?
*   **Zero Manual Entry**: Project Managers save hours every week on Jira updates and documentation.
*   **Total Accountability**: The link between "What we said in the meeting" and "What is in Jira" is 100% accurate.
*   **Continuous Improvement**: By comparing planning vs. review, the AI learns your team's true capacity, leading to more realistic goals every single month.

---
*AgileMindTools: Automating the management, so you can focus on the mission.*
