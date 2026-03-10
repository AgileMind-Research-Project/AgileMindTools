# ✂️ AI-Powered Task Splitting: A Simple Guide

Welcome to the **AgileMindTools Task Splitting Module**! This guide explains how our AI helps break down large, complex items into smaller, manageable pieces to help your team work faster and more accurately.

---

## 🌟 What is the Purpose? 
Often, a single "Task" in a project is actually too big for one person to handle at once. If it's too large, it becomes hard to estimate, hard to track, and easy to fail.

Our **Task Splitting Module** act as a precision tool that "dissects" your large tasks. It identifies the different components within a single description and automatically creates a set of smaller **Subtasks** so your team can focus on one piece at a time.

---

## ⚙️ The Technology: "The Smart Dissector"
This module uses specialized Machine Learning to understand the "weight" and "structure" of your work:

### 1. The Keyword Highlighter (TF-IDF)
*   **Context Discovery**: The AI scans your task and highlights the most important "keywords." 
*   **Relevance**: It ignores common words and focuses on the technical or functional terms that define what actually needs to be done (like "Database," "Login," or "API").

### 2. The Pattern Recognizer (Naive Bayes)
*   **Smart Categorization**: The AI has "learned" from thousands of previous tasks. It can predict the **Priority** and **Tags** of a new subtask by comparing it to patterns it has seen before.
*   **Confidence Levels**: For every split it makes, the AI calculates a "Confidence Score." If it's not sure, it marks it for your review.

### 3. The Matchmaker (Similarity Matching)
*   **Learning from the Past**: If you've split a similar task last month, the system remembers! It uses "Similarity Matching" to ensure that your new subtasks follow the same logical structure your team is used to.

---

## 🛠️ Your Dashboard: The Frontend Experience

The **Task Splitting Dashboard** is your control center for refining work. Here is how you interact with the AI's suggestions:

### 1. The Subtask Comparison View
When the AI finishes "dissecting" a task, it presents a clear side-by-side view:
*   **Original Task**: A reminder of the big picture.
*   **Subtask List**: A breakdown of the new components, each with its own summary, estimated priority, and tags.

### 2. Monitoring Quality (Visual Flags)
The AI is honest about its work. In the frontend, you will see:
*   **Quality Scores**: Each subtask is given a "Health Score."
*   **The Review Flag**: Any subtask that falls below a certain quality threshold is marked with a **🟡 Needs Review** badge. This tells you exactly where the AI might have been a bit unsure, so you can check it first.

### 3. Taking Action (Interactive Control)
You have the final say on every split:
*   **Quick Approve**: If the AI did a perfect job, one click confirms all subtasks and saves them to your backlog.
*   **Manual Refinement**: You can click on any subtask to edit its description, change its tags, or even delete it if you feel it's redundant.
*   **Adding Your Own**: If the AI missed a small detail, you can add a manual subtask directly to the list, which the system will then remember for next time.

---

## 🔄 The Splitting Process: Step-by-Step

1.  **Feeding the AI**: You take a large backlog item with a full description.
2.  **The Extraction**: The AI "Reads" the description and pulls out the core requirements.
3.  **The Logical Split**:
    *   It identifies different "functional areas" (e.g., frontend vs. backend).
    *   It estimates the **Priority** for each small piece.
    *   It assigns **Tags** to help developers find what relates to them.
4.  **Confidence Check**: The system gives each subtask a "Quality Score." If the score is high (Excellent), it proceeds. If it's low, it asks for your input.
5.  **Final Creation**: The subtasks are saved directly to your project, linked to the original big task.

---

## 📈 Why Does This Matter?
*   **Better Accuracy**: Studies show that smaller tasks are 30% more likely to be finished on time than large ones.
*   **Team Clarity**: Every developer knows exactly what "their" small piece of the puzzle is.
*   **Easier Tracking**: You can see exactly which 3 subtasks are finished and which 2 are still pending, rather than seeing one big task stuck at "50% done" for a week.

---
*AgileMindTools: Breaking complex work into simple successes.*
