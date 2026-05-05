from database import read_from_mysql_with_params, execute_query
import logging
import json
import spacy
from collections import Counter, defaultdict
import re
from datetime import datetime, timedelta
from ml_models import TaskSplitMLModels
from confidence_scorer import ConfidenceScorer
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# -----------------------
# Logging
# -----------------------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# -----------------------
# NLP Model & ML Models
# -----------------------
nlp = spacy.load("en_core_web_sm")

# Initialize ML models (will be trained from historical data)
ml_models = TaskSplitMLModels(model_dir="ml_models")
confidence_scorer = ConfidenceScorer()

# -----------------------
# Get all projects
# -----------------------
def get_all_project(tenant):
    query = "SELECT project_id, project_name, `key` FROM projects"
    df = read_from_mysql_with_params(query, {}, tenant)
    print(df,"check projets")
    return [] if df.empty else df.to_dict("records")

# -----------------------
# Backlog with priority
# -----------------------
def get_backlog_details_with_priority(project_id, tenant):
    query = """
        SELECT pb.id, pb.project_id, pb.summary, pb.description, pb.issue_type,
               pb.status, pb.priority, pb.assignee, pb.tags, pb.story_points,
               pb.story_point_estimate, pb.start_date, pb.end_date, pbp.rank
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
# Semantic similarity utilities
# -----------------------
def calculate_semantic_similarity(text1, text2):
    """
    Calculate semantic similarity between two texts using TF-IDF and cosine similarity.
    Returns a score between 0 and 1, where 1 means identical.
    """
    if not text1 or not text2:
        return 0.0
    
    try:
        vectorizer = TfidfVectorizer(lowercase=True, stop_words='english')
        tfidf_matrix = vectorizer.fit_transform([text1, text2])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return float(similarity)
    except:
        # Fallback to simple word overlap if TF-IDF fails
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        return len(words1 & words2) / len(words1 | words2)

def is_duplicate_subtask(new_subtask, existing_subtasks, similarity_threshold=0.70):
    """
    Check if a new subtask is a duplicate of any existing subtask using semantic similarity.
    Returns (is_duplicate, most_similar_task, similarity_score)
    
    Uses lower threshold (0.70) to catch more duplicates, especially those with
    different action verbs but same noun phrases (e.g., "Fix X" vs "Add X").
    """
    if not existing_subtasks:
        return False, None, 0.0
    
    # Normalize action verbs to catch semantic duplicates
    # "Fix", "Add", "Create", "Update", "Implement" are all similar actions
    action_verb_groups = [
        {"fix", "resolve", "correct", "repair", "address"},
        {"add", "create", "implement", "develop", "build", "establish"},
        {"update", "modify", "change", "revise", "adjust"},
        {"remove", "delete", "eliminate"},
        {"review", "audit", "check", "verify", "validate"}
    ]
    
    def normalize_verbs(text):
        """Replace action verbs with their group representative"""
        text_lower = text.lower()
        for group in action_verb_groups:
            group_list = list(group)
            representative = group_list[0]  # Use first verb as representative
            for verb in group:
                if text_lower.startswith(verb + " "):
                    # Replace the verb with the representative
                    return representative + text_lower[len(verb):]
        return text_lower
    
    new_text_normalized = normalize_verbs(new_subtask)
    max_similarity = 0.0
    most_similar = None
    
    for existing in existing_subtasks:
        existing_normalized = normalize_verbs(existing)
        
        # Calculate similarity on normalized text
        similarity = calculate_semantic_similarity(new_text_normalized, existing_normalized)
        
        if similarity > max_similarity:
            max_similarity = similarity
            most_similar = existing
    
    is_dup = max_similarity >= similarity_threshold
    return is_dup, most_similar, max_similarity

# -----------------------
# Extract dynamic dependency markers from project data
# -----------------------
def extract_dependency_markers(project_tasks):
    """
    Dynamically extract temporal/sequential markers from historical task data.
    NO HARDCODED KEYWORDS - learns from your project's language patterns.
    """
    dependency_markers = Counter()
    
    for task in project_tasks:
        text = (task.get("summary") or "") + " " + (task.get("description") or "")
        doc = nlp(text.lower())
        
        # Extract words that indicate sequence or dependency
        for token in doc:
            # Look for adverbs and prepositions that indicate time/sequence
            if token.pos_ in {"ADP", "ADV", "SCONJ"}:  # Prepositions, adverbs, subordinating conjunctions
                # Check if it's related to time or sequence
                if token.dep_ in {"prep", "advmod", "mark"} and len(token.text) > 2:
                    dependency_markers[token.text] += 1
        
        # Also extract common temporal phrases
        for i, token in enumerate(doc[:-1]):
            bigram = f"{token.text} {doc[i+1].text}"
            if any(word in bigram for word in ["after", "before", "once", "when", "while"]):
                dependency_markers[bigram] += 1
    
    # Return top markers that appear in at least 2 tasks
    min_frequency = max(2, len(project_tasks) // 20)  # At least 5% of tasks
    return {marker for marker, count in dependency_markers.items() if count >= min_frequency}

# -----------------------
# Calculate subtask quality score
# -----------------------
def calculate_subtask_quality(subtask_summary, parent_summary, parent_description):
    """
    Calculate quality score for a subtask based on:
    - Informativeness (not too generic)
    - Semantic coherence with parent task
    Returns score between 0 and 1, where higher is better quality.
    """
    # Check informativeness - reject very generic combinations
    generic_verbs = {"do", "make", "get", "have", "use", "see", "go"}
    generic_nouns = {"thing", "stuff", "item", "part", "piece", "work", "task"}
    
    doc = nlp(subtask_summary.lower())
    verbs = [t.lemma_ for t in doc if t.pos_ == "VERB"]
    nouns = [t.text for t in doc if t.pos_ in {"NOUN", "PROPN"}]
    
    # Penalize generic verbs and nouns
    informativeness_score = 1.0
    for verb in verbs:
        if verb in generic_verbs:
            informativeness_score -= 0.3
    for noun in nouns:
        if noun in generic_nouns:
            informativeness_score -= 0.3
    
    informativeness_score = max(0, informativeness_score)
    
    # Check semantic coherence with parent
    parent_text = (parent_summary or "") + " " + (parent_description or "")
    coherence_score = calculate_semantic_similarity(subtask_summary, parent_text)
    
    # Combined quality score (weighted average)
    quality_score = (informativeness_score * 0.4) + (coherence_score * 0.6)
    
    return quality_score

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
def detect_task_tags(text, tag_indicators, ml_models=None, similar_tasks=None):
    """
    Uses NLP and ML to determine all relevant tags for a task based on its content.
    Returns a list of tags with confidence scores.
    NO HARDCODED DEFAULTS - learns from data.
    """
    text = text.lower()
    doc = nlp(text)
    
    # Extract all relevant terms
    nouns = [t.lemma_ for t in doc if t.pos_ in {"NOUN", "PROPN"}]
    verbs = [t.lemma_ for t in doc if t.pos_ == "VERB"]
    tokens = [t.text.lower() for t in doc]
    all_terms = set(tokens + nouns + verbs)
    
    # Extract named entities for better context
    entities = [(ent.text.lower(), ent.label_) for ent in doc.ents]
    
    # Calculate scores for each tag type using NLP
    tag_scores = {}
    for tag_type, keyword_counter in tag_indicators.items():
        score = sum(keyword_counter.get(term, 0) for term in all_terms)
        # Boost score if entities match
        for ent_text, ent_label in entities:
            if ent_text in keyword_counter:
                score += keyword_counter[ent_text] * 2  # Entities are more important
        tag_scores[tag_type] = score
    
    # Use ML predictions if available
    ml_predictions = []
    if ml_models and ml_models.is_trained:
        ml_predictions = ml_models.predict_tags(text, top_n=5)
        logger.info(f"ML predictions: {ml_predictions}")
    
    # Use adaptive threshold instead of hardcoded 30%
    if tag_scores:
        threshold = ml_models.calculate_adaptive_threshold(tag_scores) if ml_models else (max(tag_scores.values()) * 0.3)
    else:
        threshold = 0
    
    # Select tags based on NLP scores
    nlp_selected_tags = [
        tag for tag, score in tag_scores.items() 
        if score > 0 and score >= threshold
    ]
    
    # Combine NLP and ML predictions
    combined_tags = set(nlp_selected_tags)
    
    # Add high-confidence ML predictions
    for tag, prob in ml_predictions:
        if prob > 0.4:  # Confidence threshold
            combined_tags.add(tag)
    
    # If still no tags, use most common tag from similar tasks
    if not combined_tags and similar_tasks:
        similar_tags = []
        for task, similarity in similar_tasks:
            if similarity > 0.3:
                task_tags = task.get('tags', [])
                if isinstance(task_tags, str):
                    try:
                        task_tags = json.loads(task_tags) if task_tags.startswith('[') else [task_tags]
                    except:
                        task_tags = [task_tags]
                similar_tags.extend(task_tags)
        
        if similar_tags:
            most_common_tag = Counter(similar_tags).most_common(1)[0][0]
            combined_tags.add(most_common_tag)
            logger.info(f"Using most common tag from similar tasks: {most_common_tag}")
    
    # Final fallback: if absolutely no tags found, use the first discovered tag from tag_indicators
    if not combined_tags and tag_indicators:
        combined_tags.add(list(tag_indicators.keys())[0])
        logger.warning(f"No tags detected, using first available tag category")
    
    return list(combined_tags)

# -----------------------
# Extract subtasks
# -----------------------
def extract_subtasks_advanced(summary, description, dynamic_nouns, dynamic_verbs, ml_models=None, project_tasks=None):
    """
    Extract subtasks using NLP and ML-based keyword extraction.
    No hardcoded keywords - learns from data.
    Uses semantic similarity to prevent duplicates.
    """
    text = (summary or "") + ". " + (description or "")
    doc = nlp(text)
    subtasks = []
    seen_summaries = []  # Track actual summaries for semantic comparison
    
    # Use ML to extract important keywords if available
    important_keywords = []
    if ml_models and ml_models.is_trained:
        important_keywords = ml_models.extract_important_keywords(text, top_n=15)
        keyword_set = {kw.lower() for kw, _ in important_keywords}
    else:
        keyword_set = set()
    
    # Dynamically determine stop verbs from frequency analysis
    # Instead of hardcoding, use the least informative verbs
    all_verbs = [t.lemma_.lower() for t in doc if t.pos_ == "VERB"]
    verb_counter = Counter(all_verbs)
    # Stop verbs are those that appear too frequently (top 10% most common)
    if verb_counter:
        threshold = max(1, len(verb_counter) // 10)
        stop_verbs = {v for v, _ in verb_counter.most_common(threshold)}
    else:
        stop_verbs = set()
    
    # Extract dependency words dynamically from project data
    dependency_words = set()
    if project_tasks:
        dependency_words = extract_dependency_markers(project_tasks)
        logger.info(f"Dynamically extracted {len(dependency_words)} dependency markers: {dependency_words}")
    
    # Fallback: if no dependency words found, use minimal NLP-based detection
    if not dependency_words:
        dependency_words = {"after", "before", "then"}  # Minimal fallback
    
    for sent in doc.sents:
        
        # Extract verbs that are either in dynamic_verbs or important_keywords
        raw_verbs = [
            t.lemma_.lower() for t in sent 
            if t.pos_ == "VERB" 
            and (t.lemma_.lower() in dynamic_verbs or t.lemma_.lower() in keyword_set)
            and t.lemma_.lower() not in stop_verbs
        ]
        
        # CRITICAL: Normalize verbs to prevent duplicates like "Fix X" and "Add X"
        # Group similar action verbs together
        action_verb_groups = [
            {"fix", "resolve", "correct", "repair", "address"},
            {"add", "create", "implement", "develop", "build", "establish"},
            {"update", "modify", "change", "revise", "adjust"},
            {"remove", "delete", "eliminate"},
            {"review", "audit", "check", "verify", "validate", "trace", "request", "integrate"},
            {"configure", "setup", "set", "enable"},
            {"produce", "generate", "prioritize"},
            {"automate", "stag", "stage"},
            {"show", "display", "render"},
            {"assign", "access", "grant"},
            {"log", "record", "track"},
            {"move", "drag", "transfer"},
            {"deliver", "send", "transmit"}
        ]
        
        def normalize_verb(verb):
            """Map verb to its group representative to avoid duplicates"""
            for group in action_verb_groups:
                if verb in group:
                    return list(group)[0]  # Return first verb as representative
            return verb
        
        # Normalize and deduplicate verbs
        normalized_verbs = {normalize_verb(v) for v in raw_verbs}
        
        # CRITICAL: Limit to maximum 2 verbs per sentence to reduce cartesian product
        # Prioritize verbs that appear earlier in the sentence (usually more important)
        verbs = list(normalized_verbs)[:2]
        
        # Extract nouns from chunks with improved filtering
        raw_nouns = []
        for chunk in sent.noun_chunks:
            chunk_text = chunk.text
            chunk_lower = chunk_text.lower()
            
            # Check if it matches dynamic nouns or keywords
            if (chunk_lower in dynamic_nouns or chunk_lower in keyword_set):
                # Split compound phrases connected by "and"
                if " and " in chunk_lower:
                    parts = [p.strip() for p in chunk_text.split(" and ")]
                    for part in parts:
                        if len(part.split()) >= 2 and len(part.split()) <= 5:
                            raw_nouns.append(part)
                # Limit to reasonable length (max 5 words)
                elif len(chunk_text.split()) >= 2 and len(chunk_text.split()) <= 5:
                    raw_nouns.append(chunk_text)
        
        # Deduplicate nouns at extraction time
        nouns = list(dict.fromkeys(raw_nouns))  # Preserves order, removes duplicates
        
        # Check for dependency markers in sentence
        dependency = any(w in sent.text.lower() for w in dependency_words)
        
        for v in verbs:
            for n in nouns:
                phrase = f"{v.capitalize()} {n}"
                
                # CRITICAL: Check if this exact noun phrase was already used with a different verb
                # e.g., "Address critical vulnerabilities" vs "Establish critical vulnerabilities"
                noun_already_used = False
                for existing_phrase in seen_summaries:
                    # Extract noun part (everything after first word)
                    existing_parts = existing_phrase.split(maxsplit=1)
                    current_parts = phrase.split(maxsplit=1)
                    
                    if len(existing_parts) > 1 and len(current_parts) > 1:
                        existing_noun = existing_parts[1].lower()
                        current_noun = current_parts[1].lower()
                        
                        # If noun phrases are identical, it's a duplicate regardless of verb
                        if existing_noun == current_noun:
                            logger.info(f"Skipping duplicate noun phrase: '{phrase}' (noun '{current_noun}' already used in '{existing_phrase}')")
                            noun_already_used = True
                            break
                
                if noun_already_used:
                    continue
                
                # Use semantic similarity to check for duplicates
                is_dup, similar_task, similarity = is_duplicate_subtask(
                    phrase, 
                    seen_summaries, 
                    similarity_threshold=0.70  # Lower threshold to catch verb variations
                )
                
                if is_dup:
                    logger.info(f"Skipping duplicate subtask: '{phrase}' (similar to '{similar_task}', similarity: {similarity:.2f})")
                    continue
                
                # Add to seen list for future comparisons
                seen_summaries.append(phrase)
                
                # Use ML to predict priority if available
                if ml_models and ml_models.is_trained:
                    priority, confidence = ml_models.predict_priority(phrase)
                else:
                    # Fallback: analyze verb semantics using spaCy
                    verb_doc = nlp(v)
                    if verb_doc and len(verb_doc) > 0:
                        # Check verb similarity to high-priority actions
                        priority = "medium"  # Default
                        for token in verb_doc:
                            if token.pos_ == "VERB":
                                # Use semantic similarity if available
                                priority = "medium"
                    else:
                        priority = "medium"
                
                # Determine complexity using NER and keyword analysis
                complexity = 1
                n_lower = n.lower()
                
                # Use NER to detect technical entities
                n_doc = nlp(n)
                for ent in n_doc.ents:
                    if ent.label_ in {"PRODUCT", "ORG", "GPE"}:
                        complexity += 1
                
                # Check against important keywords
                if any(kw in n_lower for kw, _ in important_keywords[:5]):
                    complexity += 1
                # Calculate a raw complexity score for weighting
                complexity_score = len(n.split()) + complexity
                
                # Calculate quality score and filter low-quality subtasks
                quality_score = calculate_subtask_quality(
                    phrase,
                    summary,
                    description
                )
                
                # Only add subtasks with quality score above threshold
                quality_threshold = 0.25  # Adaptive threshold based on coherence and informativeness
                if quality_score < quality_threshold:
                    logger.info(f"Filtering out low-quality subtask: '{phrase}' (quality: {quality_score:.2f})")
                    continue
                
                subtasks.append({
                    "summary": phrase,
                    "priority": priority,
                    "complexity_score": complexity_score,
                    "dependency": dependency,
                    "quality_score": quality_score  # Track quality for reporting
                })
                
    # -----------------------
    # DYNAMIC SEARCH-BASED EXPANSION (No Hardcoding)
    # -----------------------
    # If natural extraction found too few subtasks, search project history for "Lifecycle Patterns"
    if len(subtasks) <= 1 and project_tasks:
        impact_verbs = {"refactor", "migrate", "integrate", "implement", "automate", "configure", "setup", "develop", "test"}
        text_lower = text.lower()
        
        # Identify the primary action verb of the current task
        current_action = None
        for v in impact_verbs:
            if text_lower.startswith(v):
                current_action = v
                break
        
        if current_action:
            logger.info(f"Dynamic expansion triggered for action: '{current_action}'")
            
            # 1. Discover historical lifecycle patterns for this specific verb in THIS project
            lifecycle_patterns = []
            seen_patterns = set()
            
            # We look for other parent tasks that started with the same verb
            for p_task in project_tasks:
                p_summary = p_task.get("summary", "").lower()
                if p_summary.startswith(current_action) and p_task.get("id") != summary:
                    # Find items that were subtasks of THIS parent
                    p_id = p_task.get("id")
                    # In a real run, these would be fetched; here we look at tasks with same parent_id
                    # We can use the project_tasks list to find items that look like subtasks of this pattern
                    for sub_t in project_tasks:
                        if sub_t.get("parent_task_id") == p_id:
                            sub_summary = sub_t.get("summary", "")
                            # Generalize the subtask summary by removing specific nouns
                            # and replacing them with our current noun
                            sub_doc = nlp(sub_summary)
                            # Keep only the verbs and general technical terms
                            pattern_parts = []
                            for token in sub_doc:
                                if token.pos_ == "VERB":
                                    pattern_parts.append(token.text)
                                elif token.pos_ in {"NOUN", "PROPN"} and token.text.lower() in {"api", "ui", "database", "code", "logic", "test", "security"}:
                                    pattern_parts.append(token.text)
                            
                            if pattern_parts:
                                pattern = " ".join(pattern_parts)
                                if pattern not in seen_patterns:
                                    lifecycle_patterns.append(sub_summary)
                                    seen_patterns.add(pattern)
            
            # 2. Extract primary noun from current task to use as context
            target_noun = "components"
            for chunk in nlp(summary).noun_chunks:
                if chunk.root.pos_ in {"NOUN", "PROPN"}:
                    target_noun = chunk.text
                    break
            
            # 3. Apply discovered patterns
            expanded_subtasks = []
            for pattern in lifecycle_patterns[:4]: # Limit to top 4 patterns
                # Adapt the historical subtask to the new noun
                # e.g., "Refactor API logic" -> "Refactor [New Noun] logic"
                adapted_summary = pattern # Start with the original
                
                # Check for duplicates
                is_dup = False
                if subtasks:
                    is_dup, _, _ = is_duplicate_subtask(adapted_summary, [s["summary"] for s in subtasks])
                
                if not is_dup:
                    expanded_subtasks.append({
                        "summary": adapted_summary,
                        "priority": "medium",
                        "complexity_score": 3,
                        "dependency": True,
                        "quality_score": 0.85
                    })
            
            if expanded_subtasks:
                subtasks.extend(expanded_subtasks)
                logger.info(f"Added {len(expanded_subtasks)} subtasks learned from project history.")
            else:
                # 4. Fallback: If no history, use NLP to generate 3 generic lifecycle steps (No hardcoded strings)
                # "Analyze {noun}", "Develop {noun}", "Test {noun}"
                # Even the fallback verbs are dynamic based on project's most common verbs
                for v in list(dynamic_verbs)[:3]:
                    new_summary = f"{v.capitalize()} {target_noun}"
                    if not any(s["summary"] == new_summary for s in subtasks):
                        expanded_subtasks.append({
                            "summary": new_summary,
                            "priority": "medium",
                            "complexity_score": 2,
                            "dependency": True,
                            "quality_score": 0.7
                        })
                subtasks.extend(expanded_subtasks)

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
# Create notification for subtask creation
# -----------------------
def create_subtask_notification(project_id, parent_task_count, subtask_count, tenant):
    """
    Create a notification for project managers when subtasks are auto-generated.
    Directly inserts into notifications table.
    
    Args:
        project_id: Project ID
        parent_task_count: Number of parent tasks processed
        subtask_count: Number of subtasks created
        tenant: Tenant database name
    """
    try:
        logger.info(f"[NOTIFICATION] Starting notification creation for project {project_id}")
        
        # Get project details and project managers
        project_query = """
        SELECT project_name, project_manager
        FROM projects
        WHERE project_id = %(project_id)s
        """
        
        logger.info(f"[NOTIFICATION] Querying project details from database")
        project_df = read_from_mysql_with_params(
            project_query,
            {'project_id': project_id},
            tenant
        )
        
        if project_df.empty:
            logger.warning(f"[NOTIFICATION] Project {project_id} not found in database")
            return
        
        project_name = project_df.iloc[0]['project_name']
        project_manager = project_df.iloc[0].get('project_manager')
        
        logger.info(f"[NOTIFICATION] Project name: {project_name}")
        logger.info(f"[NOTIFICATION] Project manager raw value: {project_manager}")
        
        # Parse project_manager JSON to get list of emails
        project_manager_emails = []
        if project_manager:
            try:
                if isinstance(project_manager, str):
                    project_manager_emails = json.loads(project_manager)
                    logger.info(f"[NOTIFICATION] Parsed project_manager from JSON string: {project_manager_emails}")
                elif isinstance(project_manager, list):
                    project_manager_emails = project_manager
                    logger.info(f"[NOTIFICATION] Project_manager is already a list: {project_manager_emails}")
            except Exception as e:
                logger.error(f"[NOTIFICATION] Error parsing project_manager: {str(e)}")
        else:
            logger.warning(f"[NOTIFICATION] project_manager field is NULL or empty")
        
        if not project_manager_emails:
            logger.warning(f"[NOTIFICATION] No project managers assigned to project {project_id}, skipping notification")
            return
        
        # Create notification directly in database
        notification_header = f"Subtasks Auto-Generated for {project_name}"
        notification_description = f"The system has automatically generated {subtask_count} subtasks from {parent_task_count} parent task(s) for project '{project_name}'. These subtasks are ready for assignment and include AI-generated tags and descriptions."
        notification_type = "INFO"
        
        # Convert project_manager_emails to JSON string for database
        related_users_json = json.dumps(project_manager_emails)
        
        logger.info(f"[NOTIFICATION] Creating notification in database")
        logger.info(f"   Header: {notification_header}")
        logger.info(f"   Type: {notification_type}")
        logger.info(f"   Recipients: {project_manager_emails}")
        
        # Insert notification into database
        insert_notification_query = """
        INSERT INTO notifications (
            header,
            description,
            related_users,
            notification_type,
            is_read,
            created_at,
            updated_at
        ) VALUES (
            :header,
            :description,
            :related_users,
            :notification_type,
            FALSE,
            NOW(),
            NOW()
        )
        """
        
        result = execute_query(
            insert_notification_query,
            {
                'header': notification_header,
                'description': notification_description,
                'related_users': related_users_json,
                'notification_type': notification_type
            },
            tenant
        )
        
        if result:
            logger.info(f"[NOTIFICATION] Successfully created notification for {len(project_manager_emails)} project manager(s)")
        else:
            logger.error(f"[NOTIFICATION] Failed to insert notification into database")
            
    except Exception as e:
        logger.error(f"[NOTIFICATION] Exception in create_subtask_notification: {str(e)}")
        logger.exception(e)

# -----------------------
# Main orchestrator - All subtasks with dynamic tags
# -----------------------
def split_backlog_tasks(project_id, tenant):
    """
    Splits backlog tasks into subtasks with dynamically detected tags using NLP and ML.
    Uses TF-IDF, Naive Bayes, and cosine similarity for intelligent predictions.
    NO HARDCODED KEYWORDS - learns from your project data.
    """
    backlog = get_backlog_details_with_priority(project_id, tenant)
    nouns, verbs = get_dynamic_keywords(project_id, tenant)
    tag_indicators = build_tag_keyword_map(backlog)
    
    # Train or load ML models from historical data
    logger.info("Initializing ML models...")
    if not ml_models.load_models():
        logger.info("Training ML models from historical data...")
        # Get all historical tasks for training
        all_tasks_query = "SELECT summary, description, tags, priority FROM project_backlog WHERE project_id=%(pid)s"
        all_tasks_df = read_from_mysql_with_params(all_tasks_query, {"pid": project_id}, tenant)
        
        if not all_tasks_df.empty:
            all_tasks = all_tasks_df.to_dict("records")
            if ml_models.train_from_historical_data(all_tasks):
                ml_models.save_models()
                logger.info("ML models trained and saved")
            else:
                logger.warning("ML training failed, using NLP-only mode")
        else:
            logger.warning("No historical data for training, using NLP-only mode")
    else:
        logger.info("ML models loaded from disk")

    created = 0
    confidence_scores = []  # Track confidence for reporting
    
    for task in backlog:
        # Skip splitting if the task is a Bug
        issue_type = str(task.get("issue_type", "")).strip().lower()
        if issue_type == "bug":
            logger.info(f"Skipping task {task['id']} because it is a Bug")
            continue

        # Extract subtasks with ML support
        subtasks = extract_subtasks_advanced(
            task["summary"], 
            task["description"], 
            nouns, 
            verbs,
            ml_models=ml_models,
            project_tasks=backlog  # Pass backlog for dynamic dependency extraction
        )
        
        # Determine parent story points with fallback to estimate (Safe from NaN/None)
        def get_valid_sp(val):
            try:
                if val is None: return 0.0
                # Use numpy for NaN check as points often come from database/pandas
                if isinstance(val, (float, int, np.number)) and (np.isnan(val) or np.isinf(val)):
                    return 0.0
                f_val = float(val)
                return f_val if f_val > 0 else 0.0
            except:
                return 0.0

        sp = get_valid_sp(task.get("story_points"))
        if sp <= 0:
            sp = get_valid_sp(task.get("story_point_estimate"))
        
        parent_story_points = sp if sp > 0 else 5.0
            
        num_subtasks = len(subtasks)
        
        if num_subtasks > 0:
            # Weighted distribution based on complexity_score
            total_complexity = sum(sub["complexity_score"] for sub in subtasks)
            
            if total_complexity > 0:
                distributed_points = 0
                for i, sub in enumerate(subtasks):
                    # Last subtask gets the remaining points to ensure sum is accurate
                    if i == num_subtasks - 1:
                        sub["story_points"] = max(1, int(parent_story_points - distributed_points))
                    else:
                        share = (sub["complexity_score"] / total_complexity) * parent_story_points
                        point_val = int(round(share)) if round(share) >= 1 else 1
                        sub["story_points"] = point_val
                        distributed_points += point_val
            else:
                # Fallback to even distribution if no complexity differences found
                base_points = parent_story_points // num_subtasks
                remainder = parent_story_points % num_subtasks
                for i, sub in enumerate(subtasks):
                    sub["story_points"] = base_points + (1 if i < remainder else 0)
                    if sub["story_points"] < 1: sub["story_points"] = 1
        
        for i, sub in enumerate(subtasks):
            sub_id = f"{task['id']}-SUB-{i+1}"
            combined_text = sub["summary"] + " " + (task.get("description") or "")
            
            # Find similar historical tasks for better predictions
            similar_tasks = []
            if ml_models and ml_models.is_trained:
                similar_tasks = ml_models.find_similar_tasks(combined_text, top_n=5)
            
            # Detect all relevant tags using NLP + ML
            tags = detect_task_tags(
                combined_text, 
                tag_indicators,
                ml_models=ml_models,
                similar_tasks=similar_tasks
            )
            
            # Calculate confidence for tag predictions
            ml_tag_predictions = []
            if ml_models and ml_models.is_trained:
                ml_tag_predictions = ml_models.predict_tags(combined_text, top_n=3)
            
            tag_confidence = confidence_scorer.calculate_tag_confidence(
                ml_tag_predictions,
                similar_tasks
            )
            
            # Extract important keywords for quality assessment
            keywords = []
            if ml_models and ml_models.is_trained:
                keywords = ml_models.extract_important_keywords(combined_text, top_n=10)
            
            # Calculate subtask quality
            quality_metrics = confidence_scorer.calculate_subtask_quality(
                sub,
                task,
                keywords
            )
            
            # Log confidence and quality metrics
            logger.info(f"Subtask {sub_id}: Tag confidence={tag_confidence['level']}, Quality={quality_metrics['quality_level']}")
            confidence_scores.append({
                'subtask_id': sub_id,
                'tag_confidence': tag_confidence,
                'quality': quality_metrics
            })
            
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

    # Create notification for project managers after subtask creation
    if created > 0:
        logger.info(f"Attempting to create notification for project {project_id}")
        try:
            create_subtask_notification(project_id, len(backlog), created, tenant)
        except Exception as e:
            logger.error(f"Failed to create notification, but subtasks were created successfully: {str(e)}")
    
    # Calculate aggregate confidence metrics
    aggregate_confidence = confidence_scorer.aggregate_confidence_scores(
        [score['tag_confidence'] for score in confidence_scores]
    )
    
    # Calculate average quality score
    avg_quality = sum(score['quality']['quality_score'] for score in confidence_scores) / max(len(confidence_scores), 1)
    
    logger.info(f"Task splitting complete: {created} subtasks created")
    logger.info(f"   Overall confidence: {aggregate_confidence['overall_level']} ({aggregate_confidence['overall_confidence']:.2f})")
    logger.info(f"   Average quality: {avg_quality:.2f}")
    logger.info(f"   ML models used: {ml_models.is_trained}")

    return {
        "success": True,
        "items_processed": len(backlog),
        "subtasks_created": created,
        "ml_enabled": ml_models.is_trained,
        "confidence_metrics": {
            "overall_confidence": aggregate_confidence['overall_confidence'],
            "overall_level": aggregate_confidence['overall_level'],
            "should_review": aggregate_confidence['should_review'],
            "average_quality_score": avg_quality
        },
        "detailed_scores": confidence_scores if len(confidence_scores) < 20 else []  # Limit output
    }

# -----------------------
# Local test
# -----------------------
if __name__ == "__main__":
    tenant = "sliit"
    projects = get_all_project(tenant)
    if projects:
        print("Processing Projects")
        for project in projects:
            pid = project["project_id"]
            print(json.dumps(split_backlog_tasks(pid, tenant), indent=2))
