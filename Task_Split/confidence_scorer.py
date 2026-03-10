"""
Confidence Scorer for Task Splitting

Calculates confidence metrics for ML predictions and subtask quality.
Helps determine when manual review is needed.
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """
    Calculates confidence scores for task splitting predictions.
    
    Provides metrics for:
    - Tag prediction confidence
    - Subtask quality assessment
    - Aggregate confidence across all subtasks
    """
    
    # Confidence level thresholds
    THRESHOLDS = {
        'very_high': 0.85,
        'high': 0.70,
        'medium': 0.50,
        'low': 0.30,
        'very_low': 0.0
    }
    
    def __init__(self, custom_thresholds: Optional[Dict[str, float]] = None):
        """
        Initialize confidence scorer.
        
        Args:
            custom_thresholds: Optional custom confidence thresholds
        """
        if custom_thresholds:
            self.thresholds = {**self.THRESHOLDS, **custom_thresholds}
        else:
            self.thresholds = self.THRESHOLDS.copy()
    
    def _get_confidence_level(self, score: float) -> str:
        """
        Convert numeric score to confidence level.
        
        Args:
            score: Confidence score between 0 and 1
        
        Returns:
            Confidence level string
        """
        if score >= self.thresholds['very_high']:
            return 'very_high'
        elif score >= self.thresholds['high']:
            return 'high'
        elif score >= self.thresholds['medium']:
            return 'medium'
        elif score >= self.thresholds['low']:
            return 'low'
        else:
            return 'very_low'
    
    def calculate_tag_confidence(
        self, 
        predictions: List[tuple], 
        similar_tasks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate confidence for tag predictions.
        
        Args:
            predictions: List of (tag, probability) tuples from ML model
            similar_tasks: List of similar tasks with their tags
        
        Returns:
            Dict with confidence metrics:
            - level: Confidence level string
            - score: Numeric confidence (0-1)
            - factors: Breakdown of confidence factors
            - recommendations: Suggested actions
        """
        factors = {
            'ml_confidence': 0.0,
            'similar_task_support': 0.0,
            'prediction_count': len(predictions)
        }
        
        # Factor 1: Average ML prediction confidence
        if predictions:
            ml_scores = [prob for _, prob in predictions if isinstance(prob, (int, float))]
            if ml_scores:
                factors['ml_confidence'] = sum(ml_scores) / len(ml_scores)
        
        # Factor 2: Support from similar tasks
        if similar_tasks and predictions:
            predicted_tags = {tag for tag, _ in predictions}
            supporting_tasks = 0
            
            for task in similar_tasks:
                task_tags = set(task.get('tags', []))
                if predicted_tags & task_tags:  # Intersection
                    supporting_tasks += 1
            
            factors['similar_task_support'] = supporting_tasks / len(similar_tasks) if similar_tasks else 0
        
        # Calculate weighted overall confidence
        # ML confidence is primary, similar task support provides validation
        overall_score = (
            factors['ml_confidence'] * 0.7 +
            factors['similar_task_support'] * 0.3
        )
        
        # Adjust for prediction count (fewer predictions = less confident)
        if factors['prediction_count'] == 0:
            overall_score = 0.0
        elif factors['prediction_count'] == 1:
            overall_score *= 0.8  # Slight penalty for single prediction
        
        level = self._get_confidence_level(overall_score)
        
        # Generate recommendations
        recommendations = []
        if level in ['very_low', 'low']:
            recommendations.append("Consider manual tag review")
        if factors['similar_task_support'] < 0.3 and similar_tasks:
            recommendations.append("Tags differ from similar tasks - verify correctness")
        if factors['ml_confidence'] < 0.5 and predictions:
            recommendations.append("ML predictions have low confidence")
        
        return {
            'level': level,
            'score': overall_score,
            'factors': factors,
            'recommendations': recommendations
        }
    
    def calculate_subtask_quality(
        self, 
        subtask: Dict[str, Any], 
        parent_task: Dict[str, Any],
        keywords: List[tuple]
    ) -> Dict[str, Any]:
        """
        Calculate quality score for a generated subtask.
        
        Args:
            subtask: The generated subtask dict
            parent_task: The parent task dict
            keywords: Important keywords extracted from text
        
        Returns:
            Dict with quality metrics:
            - quality_level: Quality level string
            - quality_score: Numeric score (0-1)
            - factors: Breakdown of quality factors
            - issues: List of identified issues
        """
        factors = {
            'summary_length': 0.0,
            'keyword_coverage': 0.0,
            'story_point_ratio': 0.0,
            'priority_alignment': 0.0
        }
        issues = []
        
        summary = subtask.get('summary', '')
        
        # Factor 1: Summary quality (length and structure)
        if summary:
            word_count = len(summary.split())
            if 3 <= word_count <= 15:
                factors['summary_length'] = 1.0
            elif word_count < 3:
                factors['summary_length'] = 0.3
                issues.append("Summary too short")
            elif word_count <= 20:
                factors['summary_length'] = 0.7
            else:
                factors['summary_length'] = 0.5
                issues.append("Summary may be too long")
        else:
            issues.append("Missing summary")
        
        # Factor 2: Keyword coverage
        if keywords and summary:
            summary_lower = summary.lower()
            covered = sum(1 for kw, _ in keywords if kw.lower() in summary_lower)
            factors['keyword_coverage'] = min(covered / max(len(keywords) * 0.3, 1), 1.0)
        else:
            factors['keyword_coverage'] = 0.5  # Neutral if no keywords
        
        # Factor 3: Story point ratio (subtask should be smaller than parent)
        parent_points = parent_task.get('story_points', 0) or 0
        subtask_points = subtask.get('story_points', 0) or 0
        
        if parent_points > 0 and subtask_points > 0:
            ratio = subtask_points / parent_points
            if ratio <= 0.5:
                factors['story_point_ratio'] = 1.0
            elif ratio <= 0.8:
                factors['story_point_ratio'] = 0.7
            else:
                factors['story_point_ratio'] = 0.4
                issues.append("Subtask story points may be too high")
        else:
            factors['story_point_ratio'] = 0.5  # Neutral if no points
        
        # Factor 4: Priority alignment
        parent_priority = (parent_task.get('priority', 'medium') or 'medium').lower()
        subtask_priority = (subtask.get('priority', 'medium') or 'medium').lower()
        
        priority_levels = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
        parent_level = priority_levels.get(parent_priority, 2)
        subtask_level = priority_levels.get(subtask_priority, 2)
        
        # Subtask priority should be equal or lower than parent
        if subtask_level <= parent_level:
            factors['priority_alignment'] = 1.0
        else:
            factors['priority_alignment'] = 0.6
            issues.append("Subtask priority higher than parent")
        
        # Calculate weighted quality score
        quality_score = (
            factors['summary_length'] * 0.35 +
            factors['keyword_coverage'] * 0.25 +
            factors['story_point_ratio'] * 0.20 +
            factors['priority_alignment'] * 0.20
        )
        
        quality_level = self._get_confidence_level(quality_score)
        
        return {
            'quality_level': quality_level,
            'quality_score': quality_score,
            'factors': factors,
            'issues': issues
        }
    
    def aggregate_confidence_scores(
        self, 
        confidence_scores: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Aggregate confidence scores across multiple subtasks.
        
        Args:
            confidence_scores: List of confidence dicts from calculate_tag_confidence
        
        Returns:
            Dict with aggregate metrics:
            - overall_confidence: Average confidence score
            - overall_level: Aggregate confidence level
            - should_review: Whether manual review is recommended
            - distribution: Count of each confidence level
            - low_confidence_count: Number of low/very_low items
        """
        if not confidence_scores:
            return {
                'overall_confidence': 0.0,
                'overall_level': 'very_low',
                'should_review': True,
                'distribution': {},
                'low_confidence_count': 0
            }
        
        scores = []
        level_counts = {
            'very_high': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'very_low': 0
        }
        
        for conf in confidence_scores:
            score = conf.get('score', 0)
            level = conf.get('level', 'very_low')
            
            scores.append(score)
            if level in level_counts:
                level_counts[level] += 1
        
        overall_confidence = sum(scores) / len(scores)
        overall_level = self._get_confidence_level(overall_confidence)
        
        low_confidence_count = level_counts['low'] + level_counts['very_low']
        
        # Recommend review if:
        # - Overall confidence is low
        # - More than 20% of items have low confidence
        # - Any item has very_low confidence
        should_review = (
            overall_level in ['low', 'very_low'] or
            low_confidence_count > len(scores) * 0.2 or
            level_counts['very_low'] > 0
        )
        
        return {
            'overall_confidence': overall_confidence,
            'overall_level': overall_level,
            'should_review': should_review,
            'distribution': level_counts,
            'low_confidence_count': low_confidence_count
        }
