"""
Comparison script to demonstrate differences between 
rule-based and AI-powered task assignment systems.
"""

import sys
import logging
from typing import List, Dict
import numpy as np

# Import both systems
from assignee import assign_tasks_to_developers as old_assign
from ai_assignee import AITaskAssigner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AssignmentComparator:
    """Compare old rule-based vs new AI-powered assignment systems."""
    
    def __init__(self, tenant_table: str, tenant_db: str):
        self.tenant_table = tenant_table
        self.tenant_db = tenant_db
        self.ai_assigner = AITaskAssigner(tenant_table, tenant_db)
    
    def run_comparison(self, project_id: int) -> Dict:
        """
        Run both assignment systems and compare results.
        
        Returns:
            Dictionary with comparison metrics
        """
        print(f"\n{'='*120}")
        print(f"TASK ASSIGNMENT SYSTEM COMPARISON")
        print(f"Project ID: {project_id}")
        print(f"{'='*120}\n")
        
        # Run old system
        print("Running OLD RULE-BASED SYSTEM...")
        old_assignments = old_assign(project_id, self.tenant_table, self.tenant_db)
        
        # Run new AI system
        print("Running NEW AI-POWERED SYSTEM...\n")
        new_assignments = self.ai_assigner.run_assignment(project_id, save_to_db=False)
        
        # Compare results
        comparison = self._compare_assignments(old_assignments, new_assignments)
        
        # Display results
        self._display_comparison(old_assignments, new_assignments, comparison)
        
        return comparison
    
    def _compare_assignments(self, old: List[Dict], new: List[Dict]) -> Dict:
        """Compare assignment results."""
        comparison = {
            'total_tasks': len(new),
            'same_assignments': 0,
            'different_assignments': 0,
            'old_only': 0,
            'new_only': 0,
            'avg_confidence': 0,
            'high_confidence_count': 0,
            'developer_distribution_old': {},
            'developer_distribution_new': {}
        }
        
        # Create lookup dictionaries
        old_dict = {a['task_id']: a['assignee'] for a in old}
        new_dict = {a['task_id']: a['assignee'] for a in new}
        
        # Compare assignments
        all_task_ids = set(old_dict.keys()) | set(new_dict.keys())
        
        for task_id in all_task_ids:
            old_assignee = old_dict.get(task_id)
            new_assignee = new_dict.get(task_id)
            
            if old_assignee and new_assignee:
                if old_assignee == new_assignee:
                    comparison['same_assignments'] += 1
                else:
                    comparison['different_assignments'] += 1
            elif old_assignee and not new_assignee:
                comparison['old_only'] += 1
            elif new_assignee and not old_assignee:
                comparison['new_only'] += 1
        
        # Calculate confidence metrics
        if new:
            confidences = [a['confidence'] for a in new]
            comparison['avg_confidence'] = np.mean(confidences)
            comparison['high_confidence_count'] = sum(1 for c in confidences if c >= 70)
        
        # Developer distribution
        for assignment in old:
            assignee = assignment['assignee']
            comparison['developer_distribution_old'][assignee] = \
                comparison['developer_distribution_old'].get(assignee, 0) + 1
        
        for assignment in new:
            assignee = assignment['assignee']
            comparison['developer_distribution_new'][assignee] = \
                comparison['developer_distribution_new'].get(assignee, 0) + 1
        
        return comparison
    
    def _display_comparison(self, old: List[Dict], new: List[Dict], comparison: Dict):
        """Display comparison results."""
        
        print(f"\n{'='*120}")
        print("COMPARISON SUMMARY")
        print(f"{'='*120}\n")
        
        # Basic metrics
        print(f"Total Tasks Assigned:")
        print(f"  Old System: {len(old)}")
        print(f"  New System: {len(new)}")
        print()
        
        # Assignment comparison
        print(f"Assignment Comparison:")
        print(f"  Same Assignments: {comparison['same_assignments']}")
        print(f"  Different Assignments: {comparison['different_assignments']}")
        if comparison['same_assignments'] + comparison['different_assignments'] > 0:
            agreement_rate = (comparison['same_assignments'] / 
                            (comparison['same_assignments'] + comparison['different_assignments'])) * 100
            print(f"  Agreement Rate: {agreement_rate:.1f}%")
        print()
        
        # AI metrics
        print(f"AI System Metrics:")
        print(f"  Average Confidence: {comparison['avg_confidence']:.2f}%")
        print(f"  High Confidence (≥70%): {comparison['high_confidence_count']}/{len(new)}")
        if len(new) > 0:
            high_conf_rate = (comparison['high_confidence_count'] / len(new)) * 100
            print(f"  High Confidence Rate: {high_conf_rate:.1f}%")
        print()
        
        # Developer distribution
        print(f"Developer Workload Distribution:")
        print(f"\n  OLD SYSTEM:")
        for dev, count in sorted(comparison['developer_distribution_old'].items(), 
                                key=lambda x: x[1], reverse=True):
            print(f"    {dev}: {count} tasks")
        
        print(f"\n  NEW AI SYSTEM:")
        for dev, count in sorted(comparison['developer_distribution_new'].items(), 
                                key=lambda x: x[1], reverse=True):
            print(f"    {dev}: {count} tasks")
        print()
        
        # Detailed task-by-task comparison
        print(f"\n{'='*120}")
        print("DETAILED TASK COMPARISON")
        print(f"{'='*120}\n")
        
        # Create lookup dictionaries
        old_dict = {a['task_id']: a for a in old}
        new_dict = {a['task_id']: a for a in new}
        
        # Show tasks with different assignments
        different_tasks = []
        for task_id in new_dict.keys():
            if task_id in old_dict:
                if old_dict[task_id]['assignee'] != new_dict[task_id]['assignee']:
                    different_tasks.append(task_id)
        
        if different_tasks:
            print(f"Tasks with Different Assignments ({len(different_tasks)}):\n")
            print(f"{'Task ID':<20} {'Old Assignee':<35} {'New Assignee':<35} {'Confidence':<12} {'Summary'}")
            print("-" * 120)
            
            for task_id in different_tasks[:10]:  # Show first 10
                old_a = old_dict[task_id]
                new_a = new_dict[task_id]
                
                summary = new_a['summary'][:40] + "..." if len(new_a['summary']) > 40 else new_a['summary']
                confidence = f"{new_a['confidence']:.1f}%"
                
                print(f"{task_id:<20} {old_a['assignee']:<35} {new_a['assignee']:<35} {confidence:<12} {summary}")
                
                # Show score breakdown for high-confidence changes
                if new_a['confidence'] >= 70:
                    breakdown = new_a['score_breakdown']
                    print(f"  └─ AI Reasoning: Skill={breakdown['skill_match']}, "
                          f"History={breakdown['history_match']}, "
                          f"Workload={breakdown['workload_balance']}, "
                          f"AI-Sim={breakdown['ai_similarity']}, "
                          f"AI-Pred={breakdown['ai_prediction']}")
            
            if len(different_tasks) > 10:
                print(f"\n  ... and {len(different_tasks) - 10} more")
        else:
            print("All assignments are identical between systems.")
        
        print(f"\n{'='*120}")
        
        # Recommendations
        print("\nRECOMMENDATIONS:")
        print("-" * 120)
        
        if comparison['avg_confidence'] >= 75:
            print("✓ HIGH CONFIDENCE: The AI system has high confidence in its assignments.")
            print("  Recommendation: Consider using the AI system for production assignments.")
        elif comparison['avg_confidence'] >= 60:
            print("⚠ MODERATE CONFIDENCE: The AI system has moderate confidence.")
            print("  Recommendation: Review high-confidence assignments, use rule-based for low-confidence tasks.")
        else:
            print("⚠ LOW CONFIDENCE: The AI system needs more training data.")
            print("  Recommendation: Continue using rule-based system while collecting more historical data.")
        
        print()
        
        if comparison['different_assignments'] > comparison['same_assignments']:
            print("⚠ SIGNIFICANT DIFFERENCES: Many assignments differ between systems.")
            print("  Recommendation: Review the different assignments to understand AI reasoning.")
        else:
            print("✓ GOOD AGREEMENT: Most assignments agree between systems.")
            print("  Recommendation: The AI system validates the rule-based approach.")
        
        print()
        
        # Workload balance analysis
        old_workloads = list(comparison['developer_distribution_old'].values())
        new_workloads = list(comparison['developer_distribution_new'].values())
        
        if old_workloads and new_workloads:
            old_std = np.std(old_workloads)
            new_std = np.std(new_workloads)
            
            print(f"WORKLOAD BALANCE ANALYSIS:")
            print(f"  Old System Std Dev: {old_std:.2f}")
            print(f"  New System Std Dev: {new_std:.2f}")
            
            if new_std < old_std:
                improvement = ((old_std - new_std) / old_std) * 100
                print(f"  ✓ AI system provides {improvement:.1f}% better workload balance")
            elif new_std > old_std:
                decline = ((new_std - old_std) / old_std) * 100
                print(f"  ⚠ AI system has {decline:.1f}% worse workload balance")
            else:
                print(f"  = Both systems have similar workload balance")
        
        print(f"\n{'='*120}\n")


def main():
    """Main execution."""
    # Configuration
    TENANT_TABLE = "sliit"
    TENANT_DB = "agilemind_db"
    PROJECT_ID = 10237
    
    # Run comparison
    comparator = AssignmentComparator(TENANT_TABLE, TENANT_DB)
    comparison = comparator.run_comparison(PROJECT_ID)
    
    return comparison


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nComparison interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error running comparison: {str(e)}", exc_info=True)
        sys.exit(1)
