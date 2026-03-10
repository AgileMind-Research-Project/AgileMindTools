"""
ML Models for Task Splitting

Uses TF-IDF and Naive Bayes for tag prediction and priority classification.
No deep learning or LLMs - just efficient, classical ML techniques.
"""

import os
import pickle
import logging
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics.pairwise import cosine_similarity
from collections import Counter

logger = logging.getLogger(__name__)


class TaskSplitMLModels:
    """
    ML models for intelligent task splitting using classical ML techniques.
    
    Features:
    - Tag prediction using TF-IDF + Naive Bayes
    - Priority prediction using text classification
    - Similar task finding using cosine similarity
    - Keyword extraction using TF-IDF scores
    """
    
    def __init__(self, model_dir="ml_models"):
        """
        Initialize ML models.
        
        Args:
            model_dir: Directory to save/load model files
        """
        self.model_dir = model_dir
        self.model_path = os.path.join(model_dir, "task_split_models.pkl")
        
        # Models
        self.tfidf_vectorizer = None
        self.tag_classifier = None
        self.priority_classifier = None
        self.priority_encoder = None
        
        # Training data references
        self.task_texts = []
        self.task_vectors = None
        self.task_tags = []
        
        # State
        self._is_trained = False
        
        # Ensure model directory exists
        os.makedirs(model_dir, exist_ok=True)
    
    @property
    def is_trained(self):
        """Check if models are trained and ready."""
        return self._is_trained
    
    def load_models(self):
        """
        Load pre-trained models from disk.
        
        Returns:
            bool: True if models loaded successfully, False otherwise
        """
        if not os.path.exists(self.model_path):
            logger.info(f"No saved models found at {self.model_path}")
            return False
        
        try:
            with open(self.model_path, 'rb') as f:
                data = pickle.load(f)
            
            self.tfidf_vectorizer = data.get('tfidf_vectorizer')
            self.tag_classifier = data.get('tag_classifier')
            self.priority_classifier = data.get('priority_classifier')
            self.priority_encoder = data.get('priority_encoder')
            self.task_texts = data.get('task_texts', [])
            self.task_vectors = data.get('task_vectors')
            self.task_tags = data.get('task_tags', [])
            
            self._is_trained = (
                self.tfidf_vectorizer is not None and 
                self.task_vectors is not None and
                len(self.task_texts) > 0
            )
            
            logger.info(f"Models loaded successfully. Trained: {self._is_trained}")
            return self._is_trained
            
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            return False
    
    def save_models(self):
        """Save trained models to disk."""
        if not self._is_trained:
            logger.warning("Cannot save - models not trained")
            return False
        
        try:
            data = {
                'tfidf_vectorizer': self.tfidf_vectorizer,
                'tag_classifier': self.tag_classifier,
                'priority_classifier': self.priority_classifier,
                'priority_encoder': self.priority_encoder,
                'task_texts': self.task_texts,
                'task_vectors': self.task_vectors,
                'task_tags': self.task_tags
            }
            
            with open(self.model_path, 'wb') as f:
                pickle.dump(data, f)
            
            logger.info(f"Models saved to {self.model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save models: {e}")
            return False
    
    def train_from_historical_data(self, tasks):
        """
        Train models from historical task data.
        
        Args:
            tasks: List of dicts with 'summary', 'description', 'tags', 'priority'
        
        Returns:
            bool: True if training successful
        """
        if not tasks or len(tasks) < 5:
            logger.warning(f"Insufficient training data: {len(tasks) if tasks else 0} tasks (need at least 5)")
            return False
        
        try:
            # Prepare text data
            texts = []
            tags_list = []
            priorities = []
            
            for task in tasks:
                summary = task.get('summary', '') or ''
                description = task.get('description', '') or ''
                text = f"{summary}. {description}".strip()
                
                if text:
                    texts.append(text)
                    
                    # Parse tags
                    task_tags = task.get('tags', '[]')
                    if isinstance(task_tags, str):
                        try:
                            import json
                            task_tags = json.loads(task_tags)
                        except:
                            task_tags = []
                    tags_list.append(task_tags if task_tags else [])
                    
                    # Parse priority
                    priority = task.get('priority', 'medium') or 'medium'
                    priorities.append(priority.lower())
            
            if len(texts) < 5:
                logger.warning("Not enough valid tasks for training")
                return False
            
            # Train TF-IDF vectorizer
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words='english',
                ngram_range=(1, 2),
                min_df=1,
                max_df=0.95
            )
            self.task_vectors = self.tfidf_vectorizer.fit_transform(texts)
            self.task_texts = texts
            self.task_tags = tags_list
            
            # Train tag classifier (multi-label)
            # Flatten tags for training
            all_tags = set()
            for tags in tags_list:
                all_tags.update(tags)
            
            if all_tags:
                self.tag_classifier = {}
                for tag in all_tags:
                    # Binary classification for each tag
                    y = [1 if tag in task_tags else 0 for task_tags in tags_list]
                    if sum(y) >= 2:  # Only train if tag appears at least twice
                        clf = MultinomialNB(alpha=0.1)
                        clf.fit(self.task_vectors, y)
                        self.tag_classifier[tag] = clf
                        
                logger.info(f"Trained classifiers for {len(self.tag_classifier)} tags")
            
            # Train priority classifier
            unique_priorities = list(set(priorities))
            if len(unique_priorities) > 1:
                self.priority_encoder = LabelEncoder()
                y_priority = self.priority_encoder.fit_transform(priorities)
                self.priority_classifier = MultinomialNB(alpha=0.1)
                self.priority_classifier.fit(self.task_vectors, y_priority)
                logger.info(f"Trained priority classifier for {unique_priorities}")
            
            self._is_trained = True
            logger.info(f"Training complete: {len(texts)} tasks processed")
            return True
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return False
    
    def predict_tags(self, text, top_n=5):
        """
        Predict tags for given text.
        
        Args:
            text: Input text to classify
            top_n: Maximum number of tags to return
        
        Returns:
            List of (tag, probability) tuples
        """
        if not self._is_trained or not self.tag_classifier:
            return []
        
        try:
            text_vector = self.tfidf_vectorizer.transform([text])
            predictions = []
            
            for tag, clf in self.tag_classifier.items():
                proba = clf.predict_proba(text_vector)[0]
                # Get probability for positive class (tag present)
                if len(proba) > 1:
                    prob = proba[1]
                else:
                    prob = proba[0] if clf.classes_[0] == 1 else 0
                
                if prob > 0.3:  # Minimum threshold
                    predictions.append((tag, prob))
            
            # Sort by probability and return top N
            predictions.sort(key=lambda x: x[1], reverse=True)
            return predictions[:top_n]
            
        except Exception as e:
            logger.error(f"Tag prediction failed: {e}")
            return []
    
    def predict_priority(self, text):
        """
        Predict priority for given text.
        
        Args:
            text: Input text to classify
        
        Returns:
            Tuple of (priority_level, confidence)
        """
        if not self._is_trained or not self.priority_classifier:
            return ("medium", 0.5)
        
        try:
            text_vector = self.tfidf_vectorizer.transform([text])
            proba = self.priority_classifier.predict_proba(text_vector)[0]
            pred_idx = np.argmax(proba)
            confidence = proba[pred_idx]
            priority = self.priority_encoder.inverse_transform([pred_idx])[0]
            
            return (priority, confidence)
            
        except Exception as e:
            logger.error(f"Priority prediction failed: {e}")
            return ("medium", 0.5)
    
    def find_similar_tasks(self, text, top_n=5):
        """
        Find similar tasks using cosine similarity.
        
        Args:
            text: Input text to compare
            top_n: Number of similar tasks to return
        
        Returns:
            List of dicts with 'text', 'similarity', 'tags'
        """
        if not self._is_trained or self.task_vectors is None:
            return []
        
        try:
            text_vector = self.tfidf_vectorizer.transform([text])
            similarities = cosine_similarity(text_vector, self.task_vectors)[0]
            
            # Get top N indices (excluding exact matches)
            top_indices = np.argsort(similarities)[::-1]
            
            similar_tasks = []
            for idx in top_indices[:top_n]:
                similarity = similarities[idx]
                if similarity < 0.99:  # Exclude exact matches
                    similar_tasks.append({
                        'text': self.task_texts[idx],
                        'similarity': float(similarity),
                        'tags': self.task_tags[idx] if idx < len(self.task_tags) else []
                    })
            
            return similar_tasks
            
        except Exception as e:
            logger.error(f"Similar task search failed: {e}")
            return []
    
    def extract_important_keywords(self, text, top_n=10):
        """
        Extract important keywords using TF-IDF scores.
        
        Args:
            text: Input text to analyze
            top_n: Number of keywords to return
        
        Returns:
            List of (keyword, score) tuples
        """
        if not self._is_trained or not self.tfidf_vectorizer:
            return []
        
        try:
            text_vector = self.tfidf_vectorizer.transform([text])
            feature_names = self.tfidf_vectorizer.get_feature_names_out()
            
            # Get TF-IDF scores for this text
            scores = text_vector.toarray()[0]
            
            # Get top keywords
            top_indices = np.argsort(scores)[::-1][:top_n]
            keywords = [
                (feature_names[idx], float(scores[idx])) 
                for idx in top_indices 
                if scores[idx] > 0
            ]
            
            return keywords
            
        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}")
            return []
    
    def calculate_adaptive_threshold(self, tag_scores):
        """
        Calculate adaptive threshold based on score distribution.
        
        Args:
            tag_scores: Dict of tag -> score
        
        Returns:
            float: Adaptive threshold value
        """
        if not tag_scores:
            return 0
        
        scores = list(tag_scores.values())
        
        # Use median-based threshold for robustness
        if len(scores) >= 3:
            sorted_scores = sorted(scores)
            median = sorted_scores[len(sorted_scores) // 2]
            max_score = max(scores)
            
            # Threshold is between median and 30% of max
            threshold = max(median * 0.7, max_score * 0.25)
        else:
            # Fallback for small score sets
            threshold = max(scores) * 0.3
        
        return threshold
