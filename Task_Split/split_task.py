from database import read_from_mysql_with_params, execute_query
import logging
import json
import spacy
from collections import Counter, defaultdict
import re
from datetime import datetime, timedelta

# -----------------------
# Logging
# -----------------------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# -----------------------
# NLP Model
# -----------------------
nlp = spacy.load("en_core_web_sm")

# -----------------------
# Get all projects
# -----------------------
def get_all_project(tenant):
    query = "SELECT project_id, project_name, `key` FROM projects WHERE project_id = 10237"
    df = read_from_mysql_with_params(query, {}, tenant)
    return [] if df.empty else df.to_dict("records")

# -----------------------
# Backlog with priority
# -----------------------
def get_backlog_details_with_priority(project_id, tenant):
    query = """
        SELECT pb.id, pb.project_id, pb.summary, pb.description, pb.issue_type,
               pb.status, pb.priority, pb.assignee, pb.tags, pb.story_points,
               pb.start_date, pb.end_date, pbp.rank
        FROM project_backlog pb
        JOIN project_backlog_priority pbp
          ON pb.id = pbp.backlog_id
        WHERE pb.project_id = %(project_id)s
          AND pbp.sprint_id IS NULL
        ORDER BY pbp.rank
    """
    df = read_from_mysql_with_params(query, {"project_id": project_id}, tenant)
    return [] if df.empty else df.to_dict("records")

# -----------------------
# Dynamic nouns & verbs
# -----------------------
def get_dynamic_keywords(project_id, tenant):
    df = read_from_mysql_with_params(
        "SELECT summary, description FROM project_backlog WHERE project_id=%(pid)s",
        {"pid": project_id},
        tenant
    )
    noun_counter = Counter()
    verb_counter = Counter()
    for row in df.to_dict("records"):
        doc = nlp((row["summary"] or "") + ". " + (row["description"] or ""))
        for chunk in doc.noun_chunks:
            noun_counter[chunk.text.lower()] += 1
        for token in doc:
            if token.pos_ == "VERB":
                verb_counter[token.lemma_.lower()] += 1
    return ([n for n,_ in noun_counter.most_common(100)],
            [v for v,_ in verb_counter.most_common(100)])

# -----------------------
# Build multi-tag keyword map using pure NLP - NO HARDCODING
# -----------------------
def build_tag_keyword_map(project_tasks):
    """
    Dynamically discovers tag categories from existing tasks using pure NLP.
    No hardcoded tag names - learns entirely from your data.
    """
    tag_categories = defaultdict(Counter)
    
    # Step 1: Discover existing tag categories from the data
    discovered_tags = set()
    for task in project_tasks:
        existing_tags = task.get("tags")
        if existing_tags:
            if isinstance(existing_tags, str):
                try:
                    tag_list = json.loads(existing_tags) if existing_tags.startswith('[') else [existing_tags]
                except:
                    tag_list = [existing_tags]
            else:
                tag_list = existing_tags if isinstance(existing_tags, list) else []
            
            # Split pipe-separated tags and add individually
            for tag in tag_list:
                if isinstance(tag, str):
                    # Split on pipe character if present
                    if '|' in tag:
                        sub_tags = [t.strip() for t in tag.split('|') if t.strip()]
                        for sub_tag in sub_tags:
                            discovered_tags.add(sub_tag.lower())
                    else:
                        discovered_tags.add(tag.lower().strip())
    
    # Step 2: Learn word associations for each discovered tag
    for task in project_tasks:
        text = (task.get("summary") or "") + " " + (task.get("description") or "")
        doc = nlp(text.lower())
        
        # Extract linguistic features
        nouns = [t.lemma_ for t in doc if t.pos_ in {"NOUN", "PROPN"}]
        verbs = [t.lemma_ for t in doc if t.pos_ == "VERB"]
        adjectives = [t.lemma_ for t in doc if t.pos_ == "ADJ"]
        all_terms = nouns + verbs + adjectives
        
        # Get tags for this task
        existing_tags = task.get("tags")
        if existing_tags:
            if isinstance(existing_tags, str):
                try:
                    tag_list = json.loads(existing_tags) if existing_tags.startswith('[') else [existing_tags]
                except:
                    tag_list = [existing_tags]
            else:
                tag_list = existing_tags if isinstance(existing_tags, list) else []
            
            # Associate words with tags (split pipe-separated tags)
            for tag in tag_list:
                if isinstance(tag, str):
                    # Split on pipe character if present
                    if '|' in tag:
                        sub_tags = [t.strip() for t in tag.split('|') if t.strip()]
                        for sub_tag in sub_tags:
                            tag_lower = sub_tag.lower()
                            for term in all_terms:
                                if term:  # Skip empty terms
                                    tag_categories[tag_lower][term] += 1
                    else:
                        tag_lower = tag.lower().strip()
                        for term in all_terms:
                            if term:  # Skip empty terms
                                tag_categories[tag_lower][term] += 1
    
    # Step 3: If no tags discovered, use NLP to auto-cluster tasks into categories
    if not discovered_tags:
        # Use noun chunks and key verbs to automatically create semantic categories
        term_frequency = Counter()
        for task in project_tasks:
            text = (task.get("summary") or "") + " " + (task.get("description") or "")
            doc = nlp(text.lower())
            
            # Collect significant terms
            for token in doc:
                if token.pos_ in {"NOUN", "PROPN", "VERB"} and len(token.text) > 3:
                    term_frequency[token.lemma_] += 1
        
        # Get top terms to use as auto-discovered category names
        top_terms = [term for term, count in term_frequency.most_common(20) if count > 1]
        
        # Create categories based on semantic similarity
        for term in top_terms:
            discovered_tags.add(term)
            # Associate related words with this category
            for task in project_tasks:
                text = (task.get("summary") or "") + " " + (task.get("description") or "")
                doc = nlp(text.lower())
                
                # If the task mentions this term, associate all its words
                if term in text.lower():
                    for token in doc:
                        if token.pos_ in {"NOUN", "VERB", "PROPN"}:
                            tag_categories[term][token.lemma_] += 1
    
    return tag_categories

# -----------------------
# Detect task tags using NLP
# -----------------------
def detect_task_tags(text, tag_indicators):
    """
    Uses NLP to determine all relevant tags for a task based on its content.
    Returns a list of tags (backend, frontend, qa, testing, devops, etc.)
    """
    text = text.lower()
    doc = nlp(text)
    
    # Extract all relevant terms
    nouns = [t.lemma_ for t in doc if t.pos_ in {"NOUN", "PROPN"}]
    verbs = [t.lemma_ for t in doc if t.pos_ == "VERB"]
    tokens = [t.text.lower() for t in doc]
    all_terms = set(tokens + nouns + verbs)
    
    # Calculate scores for each tag type
    tag_scores = {}
    for tag_type, keyword_counter in tag_indicators.items():
        score = sum(keyword_counter.get(term, 0) for term in all_terms)
        tag_scores[tag_type] = score
    
    # Select tags with significant scores
    # Use a threshold to determine which tags are relevant
    max_score = max(tag_scores.values()) if tag_scores.values() else 0
    threshold = max_score * 0.3  # 30% of the highest score
    
    selected_tags = [
        tag for tag, score in tag_scores.items() 
        if score > 0 and score >= threshold
    ]
    
    # If no tags detected, default to backend
    if not selected_tags:
        selected_tags = ["backend"]
    
    return selected_tags

# -----------------------
# Extract subtasks
# -----------------------
def extract_subtasks_advanced(summary, description, dynamic_nouns, dynamic_verbs):
    text = (summary or "") + ". " + (description or "")
    doc = nlp(text)
    subtasks = []
    seen = set()
    stop_verbs = {"be","have","do","make","use","get","set"}
    dependency_words = {"after","before","then","next"}
    for sent in doc.sents:
        dependency = any(w in sent.text.lower() for w in dependency_words)
        verbs = [t.lemma_.lower() for t in sent if t.pos_=="VERB" and t.lemma_.lower() in dynamic_verbs and t.lemma_.lower() not in stop_verbs]
        nouns = [chunk.text for chunk in sent.noun_chunks if chunk.text.lower() in dynamic_nouns and len(chunk.text.split())>=2]
        for v in verbs:
            for n in nouns:
                phrase = f"{v.capitalize()} {n}"
                key = re.sub(r"[^a-z]","",phrase.lower())
                if key in seen:
                    continue
                seen.add(key)
                priority = "high" if v in {"create","implement","design","build"} else "medium"
                complexity = 2 if any(k in n.lower() for k in {"api","database","service"}) else 1
                story_points = min(max(len(n.split())+complexity,1),8)
                subtasks.append({
                    "summary":phrase,
                    "priority":priority,
                    "story_points":story_points,
                    "dependency":dependency
                })
    return subtasks

# -----------------------
# Generate simple, natural subtask description using NLP
# -----------------------
def generate_subtask_description(parent_task, sub_summary, tags):
    """
    Generates a simple, natural description like regular task descriptions.
    Example: "Users cannot log in even with correct username and password"
    """
    # Parse the subtask summary using NLP
    doc = nlp(sub_summary)
    
    # Extract key components
    verbs = [token for token in doc if token.pos_ == "VERB"]
    nouns = [chunk for chunk in doc.noun_chunks]
    root = [token for token in doc if token.dep_ == "ROOT"]
    
    # Build natural description based on the summary structure
    if verbs and nouns:
        # Get the main verb and object
        main_verb = verbs[0]
        main_noun = nouns[0] if nouns else ""
        
        # Create a natural sentence based on the verb tense and structure
        if main_verb.tag_ in ["VB", "VBP"]:  # Base form or present
            # Imperative: "Create the user authentication system"
            description = f"{sub_summary.strip('.')}"
        elif main_verb.tag_ == "VBG":  # Gerund
            # Convert to needs: "Creating backend API" -> "Need to create backend API for user management"
            description = f"Need to {main_verb.lemma_} {' '.join([t.text for t in doc if t not in [main_verb]])}"
        else:
            # Default: use the summary as-is
            description = sub_summary
    else:
        # No clear verb structure, use summary directly
        description = sub_summary
    
    # Add contextual details based on tags (naturally integrated)
    context_parts = []
    
    # Extract parent context if useful
    parent_desc = parent_task.get('description') or ''
    parent_summary = parent_task.get('summary') or ''
    
    # Try to extract problem statement or context from parent
    if parent_desc:
        parent_doc = nlp(parent_desc[:300])  # Analyze first 300 chars
        # Look for problem statements (sentences with negative words or issues)
        for sent in parent_doc.sents:
            if any(token.text.lower() in ['not', 'cannot', 'unable', 'fail', 'error', 'issue', 'problem'] for token in sent):
                context_parts.append(sent.text.strip())
                break
    
    # Build final description
    if context_parts:
        # Add context naturally
        final_description = f"{description}. {' '.join(context_parts[:1])}"
    else:
        # Just use the main description with slight elaboration
        if parent_summary and parent_summary.lower() not in description.lower():
            final_description = f"{description} as part of {parent_summary.lower()}"
        else:
            final_description = description
    
    # Clean up and format naturally
    final_description = final_description.strip()
    if not final_description.endswith('.'):
        final_description += '.'
    
    # Capitalize first letter
    final_description = final_description[0].upper() + final_description[1:] if final_description else description
    
    return final_description

# -----------------------
# Insert subtask
# -----------------------
def insert_subtask(data, tenant):
    query = """
        INSERT INTO project_backlog
        (id, project_id, summary, description, issue_type, status,
         priority, assignee, tags, story_points,
         sprint_id, parent_task_id, start_date, end_date, is_jira)
        VALUES
        (:id, :project_id, :summary, :description, :issue_type, :status,
         :priority, :assignee, :tags, :story_points,
         :sprint_id, :parent_task_id, :start_date, :end_date, :is_jira)
    """
    return execute_query(query, data, tenant)

# -----------------------
# Main orchestrator - All subtasks with dynamic tags
# -----------------------
def split_backlog_tasks(project_id, tenant):
    """
    Splits backlog tasks into subtasks with dynamically detected tags using NLP.
    Tags are determined based on task name and description.
    Supports: backend, frontend, qa, testing, devops, documentation, database, api, security, ui
    """
    backlog = get_backlog_details_with_priority(project_id, tenant)
    nouns, verbs = get_dynamic_keywords(project_id, tenant)
    tag_indicators = build_tag_keyword_map(backlog)

    created = 0
    for task in backlog:
        subtasks = extract_subtasks_advanced(task["summary"], task["description"], nouns, verbs)
        
        # Get parent story points
        parent_story_points = task.get("story_points") or 0
        num_subtasks = len(subtasks)
        
        # Distribute parent story points among subtasks
        if num_subtasks > 0 and parent_story_points > 0:
            # Calculate base points per subtask
            base_points = parent_story_points // num_subtasks
            remainder = parent_story_points % num_subtasks
            
            # Distribute story points (give remainder to first subtasks)
            for i, sub in enumerate(subtasks):
                if i < remainder:
                    sub["story_points"] = base_points + 1
                else:
                    sub["story_points"] = base_points
        elif num_subtasks > 0:
            # If parent has no story points, distribute evenly with minimum 1
            for sub in subtasks:
                sub["story_points"] = max(1, 5 // num_subtasks)
        
        for i, sub in enumerate(subtasks):
            sub_id = f"{task['id']}-SUB-{i+1}"
            combined_text = sub["summary"] + " " + (task.get("description") or "")
            
            # Detect all relevant tags using NLP
            tags = detect_task_tags(combined_text, tag_indicators)
            
            # Generate meaningful description based on detected tags
            description = generate_subtask_description(task, sub["summary"], tags)
            
            # Create subtask with dynamically detected tags
            insert_subtask({
                "id": sub_id,
                "project_id": project_id,
                "summary": sub["summary"],
                "description": description,
                "issue_type":"sub_task",
                "status":"todo",
                "priority":sub["priority"],
                "assignee": None,
                "tags":json.dumps(tags),
                "story_points":sub["story_points"],  # Now distributed from parent
                "sprint_id":None,
                "parent_task_id":task["id"],
                "start_date": None,
                "end_date": None,
                "is_jira":0
            }, tenant)
            created += 1

    return {
        "success": True,
        "items_processed": len(backlog),
        "subtasks_created": created
    }

# -----------------------
# Local test
# -----------------------
if __name__ == "__main__":
    tenant = "sliit"
    projects = get_all_project(tenant)
    if projects:
        pid = projects[0]["project_id"]
        print(json.dumps(split_backlog_tasks(pid, tenant), indent=2))
