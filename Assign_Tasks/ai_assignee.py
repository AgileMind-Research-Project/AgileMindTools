"""
AI-Enhanced Task Assignment System
Uses machine learning techniques (TF-IDF, Naive Bayes, Cosine Similarity) 
to intelligently assign tasks to developers based on their skills and historical performance.
"""

from database import read_from_mysql_with_params, execute_query
import logging
import json
import numpy as np
from collections import defaultdict
from datetime import datetime
import re
from typing import List, Dict, Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TFIDFVectorizer:
    """
    Simple TF-IDF implementation for text vectorization.
    """
    def __init__(self):
        self.vocabulary = {}
        self.idf_scores = {}
        self.document_count = 0
        
    def tokenize(self, text: str) -> List[str]:
        """Tokenize text into words."""
        if not text:
            return []
        # Convert to lowercase and extract alphanumeric tokens
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        return tokens
    
    def fit(self, documents: List[str]):
        """Learn vocabulary and IDF scores from documents."""
        self.document_count = len(documents)
        if self.document_count == 0:
            return
        
        # Build vocabulary
        word_doc_count = defaultdict(int)
        
        for doc in documents:
            tokens = set(self.tokenize(doc))
            for token in tokens:
                word_doc_count[token] += 1
        
        # Assign indices to words
        self.vocabulary = {word: idx for idx, word in enumerate(word_doc_count.keys())}
        
        # Calculate IDF scores
        for word, doc_count in word_doc_count.items():
            self.idf_scores[word] = np.log((self.document_count + 1) / (doc_count + 1)) + 1
    
    def transform(self, documents: List[str]) -> np.ndarray:
        """Transform documents to TF-IDF vectors."""
        if not self.vocabulary:
            return np.zeros((len(documents), 0))
        
        vectors = np.zeros((len(documents), len(self.vocabulary)))
        
        for doc_idx, doc in enumerate(documents):
            tokens = self.tokenize(doc)
            if not tokens:
                continue
            
            # Calculate term frequency
            tf_counts = defaultdict(int)
            for token in tokens:
                tf_counts[token] += 1
            
            # Calculate TF-IDF
            for word, count in tf_counts.items():
                if word in self.vocabulary:
                    tf = count / len(tokens)
                    idf = self.idf_scores.get(word, 0)
                    vectors[doc_idx, self.vocabulary[word]] = tf * idf
        
        return vectors
    
    def fit_transform(self, documents: List[str]) -> np.ndarray:
        """Fit and transform in one step."""
        self.fit(documents)
        return self.transform(documents)


class NaiveBayesClassifier:
    """
    Naive Bayes classifier for learning developer preferences from historical data.
    """
    def __init__(self):
        self.class_priors = {}
        self.feature_probs = {}
        self.classes = []
        
    def fit(self, X: np.ndarray, y: List[str]):
        """Train the classifier."""
        if len(X) == 0 or len(y) == 0:
            return
        
        self.classes = list(set(y))
        n_samples = len(y)
        
        # Calculate class priors
        for cls in self.classes:
            self.class_priors[cls] = sum(1 for label in y if label == cls) / n_samples
        
        # Calculate feature probabilities for each class
        for cls in self.classes:
            cls_indices = [i for i, label in enumerate(y) if label == cls]
            cls_features = X[cls_indices]
            
            if len(cls_features) > 0:
                # Use Laplace smoothing
                self.feature_probs[cls] = (np.sum(cls_features, axis=0) + 1) / (len(cls_features) + 2)
    
    def predict_proba(self, X: np.ndarray) -> Dict[str, List[float]]:
        """Predict class probabilities."""
        if not self.classes:
            return {}
        
        probabilities = {cls: [] for cls in self.classes}
        
        for sample in X:
            sample_probs = {}
            
            for cls in self.classes:
                # Calculate log probability
                log_prob = np.log(self.class_priors[cls])
                
                for idx, feature_val in enumerate(sample):
                    if feature_val > 0:
                        prob = self.feature_probs[cls][idx]
                        log_prob += np.log(prob)
                    else:
                        prob = 1 - self.feature_probs[cls][idx]
                        log_prob += np.log(prob)
                
                sample_probs[cls] = log_prob
            
            # Normalize to probabilities
            max_log_prob = max(sample_probs.values())
            exp_probs = {cls: np.exp(prob - max_log_prob) for cls, prob in sample_probs.items()}
            total = sum(exp_probs.values())
            
            for cls in self.classes:
                probabilities[cls].append(exp_probs[cls] / total if total > 0 else 0)
        
        return probabilities


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors."""
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return np.dot(vec1, vec2) / (norm1 * norm2)


class AITaskAssigner:
    """
    AI-powered task assignment system using multiple ML techniques.
    """
    
    # Configurable stack detection mappings (can be moved to config file or database)
    STACK_KEYWORDS = {
        'backend': [
            'backend', 'api', 'database', 'server', 'microservice', 
            'service', 'rest', 'graphql', 'sql', 'nosql', 'redis',
            'kafka', 'rabbitmq', 'mongodb', 'postgresql', 'mysql',
            'node', 'express', 'django', 'flask', 'spring', 'fastapi'
        ],
        'frontend': [
            'frontend', 'ui', 'ux', 'web', 'react', 'angular', 'vue',
            'svelte', 'nextjs', 'nuxt', 'html', 'css', 'javascript',
            'typescript', 'tailwind', 'bootstrap', 'material-ui',
            'responsive', 'mobile-web', 'pwa'
        ],
        'mobile': [
            'mobile', 'android', 'ios', 'react-native', 'flutter',
            'swift', 'kotlin', 'xamarin', 'ionic', 'cordova',
            'mobile-app', 'app-development'
        ],
        'devops': [
            'devops', 'ci/cd', 'docker', 'kubernetes', 'jenkins',
            'github-actions', 'gitlab-ci', 'aws', 'azure', 'gcp',
            'terraform', 'ansible', 'deployment', 'infrastructure'
        ],
        'data': [
            'data', 'analytics', 'ml', 'ai', 'machine-learning',
            'data-science', 'etl', 'pipeline', 'spark', 'hadoop',
            'pandas', 'numpy', 'tensorflow', 'pytorch'
        ],
        'testing': [
            'testing', 'qa', 'test', 'unit-test', 'integration-test',
            'e2e', 'selenium', 'jest', 'pytest', 'cypress', 'automation'
        ]
    }
    
    
    def __init__(self, tenant_table: str, tenant_db: str):
        self.tenant_table = tenant_table
        self.tenant_db = tenant_db
        self.tfidf = TFIDFVectorizer()
        self.nb_classifier = NaiveBayesClassifier()
        self.developer_profiles = {}
        self.trained = False
    
    def fetch_developers(self, project_id: str) -> List[Dict]:
        """Fetch active developers for a project."""
        try:
            # Updated query to work with new schema (roles is a JSON column)
            sql_query = f"""
                SELECT 
                    email,
                    first_name,
                    last_name,
                    roles,
                    user_data
                FROM {self.tenant_table}
                WHERE status = 'ACTIVE'
                    AND JSON_CONTAINS(projects, '{project_id}')
                    AND JSON_CONTAINS(roles, '"DEVELOPER"', '$')
            """
            
            df = read_from_mysql_with_params(sql_query, {}, self.tenant_db)
            
            if df.empty:
                logger.warning(f"No developers found for project {project_id}")
                return []
            
            developers = []
            for _, row in df.iterrows():
                user_data = {}
                if row['user_data'] and row['user_data'] != 'null':
                    try:
                        user_data = json.loads(row['user_data']) if isinstance(row['user_data'], str) else row['user_data']
                    except json.JSONDecodeError:
                        logger.warning(f"Could not parse user_data for {row['email']}")
                
                developer = {
                    "email": row['email'],
                    "first_name": row.get('first_name') or '',
                    "last_name": row.get('last_name') or '',
                    "stack": user_data.get('stack') or [],
                    "technologies": user_data.get('technologies') or [],
                    "experience_years": user_data.get('experience_years', 0) or 0
                }
                developers.append(developer)
            
            logger.info(f"Fetched {len(developers)} developers for project {project_id}")
            return developers
            
        except Exception as e:
            logger.error(f"Error fetching developers: {str(e)}")
            return []
    
    def fetch_historical_assignments(self, project_id: int) -> Tuple[List[Dict], List[str]]:
        """Fetch completed task assignments for training."""
        try:
            query = """
                SELECT 
                    id,
                    summary,
                    description,
                    issue_type,
                    assignee,
                    tags,
                    priority,
                    story_points,
                    estimated_hours,
                    logged_hours
                FROM project_backlog
                WHERE project_id = %(project_id)s
                    AND assignee IS NOT NULL
                    AND assignee != ''
                    AND status IN ('done', 'in_progress')
                ORDER BY updated_at DESC
                LIMIT 500
            """
            
            params = {'project_id': project_id}
            df = read_from_mysql_with_params(query, params, self.tenant_table)
            
            if df.empty:
                logger.info(f"No historical assignments found for project {project_id}")
                return [], []
            
            tasks = []
            assignees = []
            
            for _, row in df.iterrows():
                task = {
                    'id': row['id'],
                    'summary': row['summary'] or '',
                    'description': row['description'] or '',
                    'issue_type': row['issue_type'] or '',
                    'tags': json.loads(row['tags']) if row['tags'] and isinstance(row['tags'], str) else (row['tags'] or []),
                    'priority': row['priority'] or '',
                    'story_points': row.get('story_points', 0) or 0,
                    'estimated_hours': row.get('estimated_hours', 0) or 0,
                    'logged_hours': row.get('logged_hours', 0) or 0
                }
                tasks.append(task)
                assignees.append(row['assignee'])
            
            logger.info(f"Fetched {len(tasks)} historical assignments")
            return tasks, assignees
            
        except Exception as e:
            logger.error(f"Error fetching historical assignments: {str(e)}")
            return [], []
    
    def build_developer_profiles(self, developers: List[Dict], historical_tasks: List[Dict], assignees: List[str]):
        """Build comprehensive developer profiles from historical data."""
        self.developer_profiles = {}
        
        for dev in developers:
            email = dev['email']
            self.developer_profiles[email] = {
                'email': email,
                'name': f"{dev.get('first_name') or ''} {dev.get('last_name') or ''}".strip(),
                'stack': dev.get('stack') or [],
                'technologies': [str(t).lower() for t in (dev.get('technologies') or [])],
                'experience_years': dev.get('experience_years', 0) or 0,
                'task_history': {
                    'total_tasks': 0,
                    'issue_types': defaultdict(int),
                    'technologies_used': defaultdict(int),
                    'avg_story_points': 0,
                    'avg_completion_ratio': 0,
                    'priorities': defaultdict(int)
                }
            }
        
        # Analyze historical assignments
        for task, assignee in zip(historical_tasks, assignees):
            if assignee not in self.developer_profiles:
                continue
            
            profile = self.developer_profiles[assignee]['task_history']
            profile['total_tasks'] += 1
            profile['issue_types'][task['issue_type']] += 1
            profile['priorities'][task['priority']] += 1
            
            # Track technology usage from tags
            task_tags = task.get('tags') or []
            for tag in task_tags:
                if isinstance(tag, str):
                    profile['technologies_used'][tag.lower()] += 1
            
            # Calculate average story points
            if task['story_points']:
                current_avg = profile['avg_story_points']
                total = profile['total_tasks']
                profile['avg_story_points'] = ((current_avg * (total - 1)) + task['story_points']) / total
            
            # Calculate completion ratio
            if task['estimated_hours'] and task['logged_hours']:
                ratio = task['logged_hours'] / task['estimated_hours']
                current_avg = profile['avg_completion_ratio']
                total = profile['total_tasks']
                profile['avg_completion_ratio'] = ((current_avg * (total - 1)) + ratio) / total
        
        logger.info(f"Built profiles for {len(self.developer_profiles)} developers")
    
    def train(self, project_id: int, developers: List[Dict]):
        """Train the AI models on historical data."""
        try:
            # Fetch historical data
            historical_tasks, assignees = self.fetch_historical_assignments(project_id)
            
            if not historical_tasks:
                logger.warning("No historical data available for training. Using rule-based assignment.")
                self.trained = False
                return
            
            # Build developer profiles
            self.build_developer_profiles(developers, historical_tasks, assignees)
            
            # Prepare documents for TF-IDF
            documents = []
            for task in historical_tasks:
                text = f"{task['summary']} {task['description']} {' '.join(task.get('tags', []))} {task['issue_type']}"
                documents.append(text)
            
            # Train TF-IDF
            self.tfidf.fit(documents)
            
            # Train Naive Bayes classifier
            task_vectors = self.tfidf.transform(documents)
            self.nb_classifier.fit(task_vectors, assignees)
            
            self.trained = True
            logger.info("AI models trained successfully")
            
        except Exception as e:
            logger.error(f"Error training AI models: {str(e)}")
            self.trained = False
    
    def extract_task_features(self, task: Dict) -> Dict:
        """Extract relevant features from a task."""
        return {
            'summary': task.get('summary') or '',
            'description': task.get('description') or '',
            'issue_type': (task.get('issue_type') or '').lower(),
            'tags': [str(t).lower() for t in (task.get('tags') or [])],
            'priority': (task.get('priority') or '').lower(),
            'story_points': task.get('story_points') or 0,
            'estimated_hours': task.get('estimated_hours') or 0
        }
    
    def detect_stack_from_tags(self, tags: List[str], issue_type: str = '') -> List[str]:
        """
        Detect which stacks are relevant based on tags and issue type.
        Uses configurable keyword mappings instead of hard-coded checks.
        
        Args:
            tags: List of task tags
            issue_type: Task issue type
        
        Returns:
            List of detected stacks (e.g., ['backend', 'frontend'])
        """
        detected_stacks = set()
        
        # Combine tags and issue_type for detection
        tags_norm = tags or []
        issue_norm = issue_type or ''
        all_keywords = [str(tag).lower() for tag in tags_norm] + [issue_norm.lower()]
        
        # Check each stack's keywords
        for stack, keywords in self.STACK_KEYWORDS.items():
            for keyword in all_keywords:
                if any(stack_keyword in keyword for stack_keyword in keywords):
                    detected_stacks.add(stack)
                    break
        
        return list(detected_stacks)
    
    def calculate_stack_match_score(self, detected_stacks: List[str], dev_stack: List[str]) -> float:
        """
        Calculate stack matching score based on detected stacks and developer stack.
        
        Args:
            detected_stacks: Stacks detected from task tags
            dev_stack: Developer's stack capabilities
        
        Returns:
            Score from 0-20 points
        """
        if not detected_stacks:
            return 0.0
        
        dev_stack_norm = dev_stack or []
        dev_stack_lower = [str(s).lower() for s in dev_stack_norm]
        
        # Calculate match ratio
        matches = sum(1 for stack in detected_stacks if stack in dev_stack_lower)
        match_ratio = matches / len(detected_stacks) if detected_stacks else 0
        
        # Award full points for perfect match, partial for partial match
        score = match_ratio * 20
        
        # Bonus for fullstack developers when multiple stacks are needed
        if len(detected_stacks) >= 2 and 'backend' in dev_stack_lower and 'frontend' in dev_stack_lower:
            score = min(20, score + 5)  # Bonus for versatility
        
        return score
        
    def calculate_skill_match_score(self, task_features: Dict, developer: Dict, project_metadata: Dict = None) -> float:
        """Calculate how well a developer's skills match the task requirements and project context."""
        score = 0.0
        
        dev_techs = set(developer.get('technologies') or [])
        task_tags = set(task_features.get('tags') or [])
        
        # 1. Technology overlap (0-40 points)
        if dev_techs and task_tags:
            tech_overlap = len(dev_techs.intersection(task_tags))
            tech_score = min(40, tech_overlap * 10)
            score += tech_score
        
        # 2. Stack matching (0-20 points) - Using flexible tag-based detection
        detected_stacks = self.detect_stack_from_tags(
            task_features['tags'], 
            task_features['issue_type']
        )
        dev_stack = developer.get('stack', [])
        stack_score = self.calculate_stack_match_score(detected_stacks, dev_stack)
        score += stack_score
        
        # 3. Project Context Alignment (0-20 points)
        if project_metadata:
            project_score = 0.0
            project_techs = set()
            
            # Helper to parse tech strings/lists
            def parse_techs(tech_input):
                if not tech_input: return []
                if isinstance(tech_input, list): return [t.lower() for t in tech_input]
                if isinstance(tech_input, str): 
                    try:
                        return [t.lower() for t in json.loads(tech_input)]
                    except:
                        return [t.strip().lower() for t in tech_input.split(',')]
                return []

            project_techs.update(parse_techs(project_metadata.get('backend_technologies')))
            project_techs.update(parse_techs(project_metadata.get('frontend_technologies')))
            
            if project_techs and dev_techs:
                proj_overlap = len(dev_techs.intersection(project_techs))
                project_score += min(15, proj_overlap * 2)

            arch_type = str(project_metadata.get('architecture_type', '')).lower()
            if arch_type:
                if arch_type in dev_techs:
                    project_score += 5
                elif 'microservice' in arch_type and ('docker' in dev_techs or 'kubernetes' in dev_techs or 'aws' in dev_techs):
                     project_score += 5
            
            score += min(20, project_score)

        # 4. Experience bonus (0-10 points)
        exp_years = developer.get('experience_years', 0)
        score += min(10, exp_years * 2)
        
        return score

    def calculate_history_match_score(self, task_features: Dict, developer_email: str) -> float:
        """Calculate score based on developer's historical performance."""
        if developer_email not in self.developer_profiles:
            return 0.0
        
        score = 0.0
        history = self.developer_profiles[developer_email]['task_history']
        
        # Issue type familiarity (0-20 points)
        issue_type = task_features['issue_type']
        if issue_type in history['issue_types']:
            type_count = history['issue_types'][issue_type]
            total_tasks = history['total_tasks']
            familiarity_ratio = type_count / total_tasks if total_tasks > 0 else 0
            score += familiarity_ratio * 20
        
        # Technology familiarity (0-20 points)
        task_tags = set(task_features.get('tags') or [])
        tech_used = history.get('technologies_used') or {}
        
        if task_tags and tech_used:
            familiar_techs = sum(tech_used.get(tag, 0) for tag in task_tags)
            total_tech_uses = sum(tech_used.values())
            tech_familiarity = familiar_techs / total_tech_uses if total_tech_uses > 0 else 0
            score += tech_familiarity * 20
        
        # Completion efficiency (0-15 points)
        completion_ratio = history['avg_completion_ratio']
        if 0.8 <= completion_ratio <= 1.2:  # Within 20% of estimate
            score += 15
        elif 0.6 <= completion_ratio <= 1.4:  # Within 40% of estimate
            score += 10
        elif completion_ratio > 0:
            score += 5
        
        # Priority handling (0-5 points)
        task_priority = task_features['priority']
        if task_priority in history['priorities']:
            score += 5
        
        return score
    
    def calculate_workload_balance_score(self, developer_email: str, current_workload: Dict[str, float]) -> float:
        """Calculate score based on current workload (prefer less loaded developers)."""
        max_workload = max(current_workload.values()) if current_workload else 0
        dev_workload = current_workload.get(developer_email, 0)
        
        if max_workload == 0:
            return 20.0
        
        workload_ratio = dev_workload / max_workload
        score = 20 * (1 - workload_ratio)
        return score
    
    def assign_with_ai(self, tasks: List[Dict], developers: List[Dict], project_id: int, project_metadata: Dict = None) -> List[Dict]:
        """Assign tasks using AI-powered scoring system."""
        if not developers:
            logger.warning("No developers available for assignment")
            return []
        
        if not self.trained:
            self.train(project_id, developers)
        
        assignments = []
        current_workload = {dev['email']: 0.0 for dev in developers}
        
        task_documents = []
        for task in tasks:
            features = self.extract_task_features(task)
            tags_str = ' '.join(features.get('tags') or [])
            text = f"{features.get('summary') or ''} {features.get('description') or ''} {tags_str} {features.get('issue_type') or ''}"
            task_documents.append(text)
        
        task_vectors = self.tfidf.transform(task_documents) if self.trained else None
        nb_predictions = self.nb_classifier.predict_proba(task_vectors) if self.trained and len(self.nb_classifier.classes) > 0 else None
        
        for task_idx, task in enumerate(tasks):
            task_features = self.extract_task_features(task)
            best_developer = None
            best_score = -1
            best_breakdown = {}
            
            for dev in developers:
                dev_email = dev['email']
                
                skill_score = self.calculate_skill_match_score(task_features, dev, project_metadata)
                history_score = self.calculate_history_match_score(task_features, dev_email)
                workload_score = self.calculate_workload_balance_score(dev_email, current_workload)
                
                similarity_score = 0.0
                nb_score = 0.0
                
                if self.trained and task_vectors is not None:
                    dev_text = f"{' '.join(dev['technologies'])} {' '.join(dev['stack'])}"
                    dev_vector = self.tfidf.transform([dev_text])[0]
                    similarity = cosine_similarity(task_vectors[task_idx], dev_vector)
                    similarity_score = similarity * 20
                    
                    if nb_predictions and dev_email in nb_predictions:
                        nb_prob = nb_predictions[dev_email][task_idx]
                        nb_score = nb_prob * 20
                
                total_score = skill_score + history_score + workload_score + similarity_score + nb_score
                
                if total_score > best_score:
                    best_score = total_score
                    best_developer = dev_email
                    best_breakdown = {
                        'skill_match': round(skill_score, 2),
                        'history_match': round(history_score, 2),
                        'workload_balance': round(workload_score, 2),
                        'ai_similarity': round(similarity_score, 2),
                        'ai_prediction': round(nb_score, 2),
                        'total': round(total_score, 2)
                    }
            
            if best_developer:
                max_possible_score = 170
                confidence = min(100, (best_score / max_possible_score) * 100)
                
                assignment = {
                    'task_id': task['id'],
                    'assignee': best_developer,
                    'summary': task_features['summary'],
                    'issue_type': task_features['issue_type'],
                    'story_points': task_features['story_points'],
                    'confidence': round(confidence, 2),
                    'score_breakdown': best_breakdown,
                    'ai_powered': self.trained
                }
                
                assignments.append(assignment)
                workload_increment = task_features['story_points'] if task_features['story_points'] > 0 else 1
                current_workload[best_developer] += workload_increment
        
        logger.info(f"AI assigned {len(assignments)} tasks with average confidence: {np.mean([a['confidence'] for a in assignments]):.2f}%")
        return assignments

    def get_unassigned_parent_tasks(self, project_id: int) -> List[str]:
        """Get parent backlog items that don't have a sprint assigned."""
        try:
            check_query = "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = %(schema)s AND TABLE_NAME = 'project_backlog_priority'"
            check_params = {'schema': self.tenant_table}
            check_df = read_from_mysql_with_params(check_query, check_params, self.tenant_table)
            
            if check_df.empty:
                logger.warning(f"Table 'project_backlog_priority' not found. Skipping project {project_id}.")
                return []

            query = "SELECT pbp.backlog_id FROM project_backlog_priority pbp WHERE pbp.project_id = %(project_id)s AND pbp.sprint_id IS NULL ORDER BY pbp.rank"
            df = read_from_mysql_with_params(query, {'project_id': project_id}, self.tenant_table)
            
            if df.empty: return []
            return df['backlog_id'].tolist()
        except Exception as e:
            logger.info(f"Skipping project {project_id}: {str(e)}")
            return []
    
    def get_subtasks_by_parent_ids(self, parent_ids: List[str]) -> List[Dict]:
        """Get all subtasks where parent_task_id matches the given parent IDs."""
        try:
            if not parent_ids: return []
            placeholders = ','.join(['%s'] * len(parent_ids))
            query = f"""
                SELECT id, project_id, summary, description, issue_type, status, priority, assignee, tags, estimated_hours, story_points, parent_task_id
                FROM project_backlog
                WHERE parent_task_id IN ({placeholders}) AND status = 'todo'
                ORDER BY priority DESC, story_points DESC
            """
            df = read_from_mysql_with_params(query, tuple(parent_ids), self.tenant_table)
            if df.empty: return []
            
            subtasks = df.to_dict('records')
            for task in subtasks:
                tags_val = task.get('tags')
                if tags_val and isinstance(tags_val, str):
                    try:
                        task['tags'] = json.loads(tags_val)
                    except:
                        task['tags'] = []
                elif tags_val is None:
                    task['tags'] = []
            return subtasks
        except Exception as e:
            logger.error(f"Error getting subtasks: {str(e)}")
            return []

    def get_unassigned_tasks(self, project_id: int) -> List[Dict]:
        """Fetch unassigned tasks using parent->subtask method."""
        try:
            parent_ids = self.get_unassigned_parent_tasks(project_id)
            if not parent_ids: 
                logger.warning(f"No unassigned parent tasks for project {project_id}")
                return []
            
            subtasks = self.get_subtasks_by_parent_ids(parent_ids)
            tasks = []
            for task in subtasks:
                if not task.get('assignee') or task.get('assignee') == '':
                    formatted_task = {
                        'id': task['id'],
                        'project_id': task['project_id'],
                        'summary': task.get('summary') or '',
                        'description': task.get('description') or '',
                        'issue_type': task.get('issue_type') or '',
                        'status': task.get('status') or 'todo',
                        'priority': task.get('priority') or '',
                        'tags': task.get('tags') or [],
                        'estimated_hours': task.get('estimated_hours') or 0,
                        'story_points': task.get('story_points') or 0,
                        'parent_task_id': task.get('parent_task_id') or ''
                    }
                    tasks.append(formatted_task)
            return tasks
        except Exception as e:
            logger.error(f"Error fetching unassigned tasks: {str(e)}")
        return []

    def save_assignments(self, assignments: List[Dict]) -> bool:
        """Save assignments to database."""
        try:
            if not assignments: return True
            # Update assignee for each task
            for assignment in assignments:
                # Use f-string to avoid driver parameter syntax issues (%(name)s vs :name)
                # Ensure values are properly quoted
                assignee_email = assignment['assignee']
                task_id = assignment['task_id']
                updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                update_query = f"""
                    UPDATE project_backlog
                    SET assignee = '{assignee_email}',
                        updated_at = '{updated_at}'
                    WHERE id = '{task_id}'
                """
                
                try:
                    execute_query(update_query, {}, self.tenant_table)
                    logger.info(f"Updated task {task_id} -> {assignee_email}")
                except Exception as e:
                    logger.error(f"Failed to update task {task_id}: {e}")
            return True
        except Exception as e:
            logger.error(f"Error saving assignments: {str(e)}")
            return False

    def get_unassigned_bugs(self, project_id: int) -> List[Dict]:
        """Fetch unassigned Bug tasks (Top-level bugs)."""
        try:
            query = """
                SELECT id, project_id, summary, description, issue_type, status, priority, assignee, tags, estimated_hours, story_points, parent_task_id
                FROM project_backlog
                WHERE project_id = %(project_id)s 
                AND issue_type = 'Bug' 
                AND (assignee IS NULL OR assignee = '')
                AND status != 'done'
            """
            df = read_from_mysql_with_params(query, {'project_id': project_id}, self.tenant_table)
            if df.empty: return []
            
            bugs = df.to_dict('records')
            # Normalize tags
            for task in bugs:
                tags_val = task.get('tags')
                if tags_val and isinstance(tags_val, str):
                    try:
                        task['tags'] = json.loads(tags_val)
                    except:
                        task['tags'] = []
                elif tags_val is None:
                    task['tags'] = []
            return bugs
        except Exception as e:
            logger.error(f"Error fetching unassigned bugs: {str(e)}")
            return []

    def assign_parents_to_manager(self, project_id: int, project_metadata: Dict) -> None:
        """
        Assign parent tasks to the Project Manager if all their subtasks are assigned.
        Scans all unassigned parent tasks in the project.
        """
        try:
            if not project_metadata:
                return

            # 1. Get Project Manager email
            pm_data = project_metadata.get('project_manager')
            pm_email = None
            
            if pm_data:
                if isinstance(pm_data, list) and len(pm_data) > 0:
                    pm_email = pm_data[0]
                elif isinstance(pm_data, str):
                    try:
                        parsed = json.loads(pm_data)
                        if isinstance(parsed, list) and len(parsed) > 0:
                            pm_email = parsed[0]
                        else:
                            pm_email = pm_data
                    except:
                        pm_email = pm_data

            if not pm_email:
                logger.warning(f"No Project Manager found for project {project_id}")
                return

            # 2. Find all unassigned Parent Tasks (Stories/Epics, excluding Bugs)
            # Use f-string for table name if needed, but here self.tenant_table is just the schema/table prefix for some helper
            # actually read_from_mysql_with_params uses the table arg as schema or table?
            # In other methods it is passed as schema.
            
            query = """
                SELECT id, summary 
                FROM project_backlog 
                WHERE project_id = %(project_id)s 
                AND (parent_task_id IS NULL OR parent_task_id = '')
                AND (assignee IS NULL OR assignee = '')
                AND issue_type != 'Bug'
            """
            
            parents_df = read_from_mysql_with_params(query, {'project_id': project_id}, self.tenant_table)
            
            if parents_df.empty:
                return
            
            ids_to_assign = []
            
            # 3. Check each parent's subtasks
            for _, parent in parents_df.iterrows():
                parent_id = parent['id']
                
                # Count subtasks
                sub_query = """
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN assignee IS NOT NULL AND assignee != '' THEN 1 END) as assigned
                    FROM project_backlog
                    WHERE parent_task_id = %s
                """
                
                # Using tuple for param to be safe with %s
                counts = read_from_mysql_with_params(sub_query, (parent_id,), self.tenant_table)
                
                if not counts.empty:
                    total = counts.iloc[0]['total']
                    assigned = counts.iloc[0]['assigned']
                    
                    # Only assign if there ARE subtasks and ALL are assigned
                    # If total=0 (no subtasks), maybe we shouldn't auto-assign to PM yet? 
                    # Requirement says "after all their subtasks have been assigned". 
                    # Implies tasks with subtasks.
                    if total > 0 and total == assigned:
                        ids_to_assign.append(parent_id)

            if not ids_to_assign:
                return

            logger.info(f"Assigning {len(ids_to_assign)} parent tasks to Project Manager: {pm_email}")

            for parent_id in ids_to_assign:
                updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                update_query = f"""
                    UPDATE project_backlog
                    SET assignee = '{pm_email}',
                        updated_at = '{updated_at}'
                    WHERE id = '{parent_id}'
                """
                try:
                    execute_query(update_query, {}, self.tenant_table)
                    logger.info(f"Assigned Parent Task {parent_id} -> Manager {pm_email}")
                except Exception as e:
                    logger.error(f"Failed to assign parent task {parent_id}: {e}")

        except Exception as e:
            logger.error(f"Error in assign_parents_to_manager: {str(e)}")

    def run_assignment(self, project_id: int, save_to_db: bool = True, project_metadata: Dict = None) -> List[Dict]:
        """Main method to run AI-powered task assignment."""
        try:
            logger.info(f"Starting AI task assignment for project {project_id}")
            developers = self.fetch_developers(str(project_id))
            
            # 1. Get Unassigned Subtasks
            subtasks = self.get_unassigned_tasks(project_id)
            
            # 2. Get Unassigned Standalone Bugs (Parent Bugs)
            bugs = self.get_unassigned_bugs(project_id)
            
            if bugs:
                logger.info(f"Found {len(bugs)} unassigned bugs to process")
            
            all_tasks = subtasks + bugs
            
            assignments = []
            if all_tasks and developers:
                # Assign both Subtasks and Bugs to Developers
                assignments = self.assign_with_ai(all_tasks, developers, project_id, project_metadata)
            
            if save_to_db:
                if assignments:
                    # 1. Save assignments (Subtasks + Bugs)
                    self.save_assignments(assignments)
                
                # 2. Assign associated parent tasks (Stories) to Project Manager
                # Run this regardless of whether new assignments were made,
                # to catch up on any manual updates or previously skipped parents.
                self.assign_parents_to_manager(project_id, project_metadata)
                
            return assignments
        except Exception as e:
            logger.error(f"Error in run_assignment: {str(e)}")
            return []

def get_all_project(tenant):
    """Retrieve all projects from the database."""
    try:
        project_query = "SELECT project_id, stack_type, backend_technologies, frontend_technologies, architecture_type, project_manager, project_name, `key` FROM projects where project_id = 10406"
        projects_df = read_from_mysql_with_params(project_query, {}, tenant)
        if projects_df.empty: return []
        return projects_df.to_dict('records')
    except Exception as e:
        logging.error(f"Error getting project list: {str(e)}")
        raise

if __name__ == "__main__":
    TENANT_TABLE = "sliit" 
    TENANT_DB = "agilemind_db"
    
    ai_assigner = AITaskAssigner(TENANT_TABLE, TENANT_DB)
    
    print(f"\n{'='*100}")
    print(f"AI-POWERED TASK ASSIGNMENT SYSTEM")
    print(f"{'='*100}\n")
    
    try:
        projects = get_all_project(TENANT_TABLE)
        
        for project in projects:
            PROJECT_ID = project['project_id']
            print(f"Processing Project: {project['project_name']} (ID: {PROJECT_ID})")
            print(f"  • Stack: {project.get('stack_type')}")
            print(f"  • Architecture: {project.get('architecture_type')}")
            
            assignments = ai_assigner.run_assignment(PROJECT_ID, save_to_db=True, project_metadata=project)
            
            if not assignments:
                print("  -> No tasks were assigned.")
            else:
                print(f"\n  ✓ Successfully assigned {len(assignments)} tasks\n")
                print(f"  {'Task ID':<20} {'Assignee':<35} {'Confidence':<12} {'Score':<8}")
                print("  " + "-" * 80)
                
                for assignment in assignments:
                    task_id = assignment['task_id']
                    assignee = assignment['assignee']
                    confidence = f"{assignment['confidence']:.1f}%"
                    total_score = assignment['score_breakdown']['total']
                    
                    print(f"  {task_id:<20} {assignee:<35} {confidence:<12} {total_score:<8}")
                    
                    if assignment['confidence'] >= 70:
                        bd = assignment['score_breakdown']
                        # Simplified breakdown print for readability
                        print(f"     [Skill: {bd['skill_match']} | Proj: Included | History: {bd['history_match']} | AI: {bd['ai_similarity']}]")
            
            print(f"\n{'-'*100}")

    except Exception as e:
        print(f"Error in main execution: {e}")
