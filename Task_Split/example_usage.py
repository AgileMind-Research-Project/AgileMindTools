"""
Example Usage: Task Splitting Evaluation Metrics

Shows how to use the evaluation system in practice.
Based on actual metrics from Component1_Results_and_Discussion.md Section 8.1-8.2

Three usage patterns:
1. Basic: No expert baseline (automatic estimation)
2. Advanced: With expert baseline (true accuracy)
3. Custom: Direct evaluator usage
"""

from evaluation_metrics import TaskSplittingEvaluator, calculate_metrics_from_split_results
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger()


# ============================================================================
# PATTERN 1: Basic Usage (No Expert Baseline)
# ============================================================================

def example_1_basic_usage():
    """
    Simplest usage: just call split_backlog_tasks and get metrics back.

    Evaluation is enabled by default.
    Without expert baseline, precision/recall are estimated from filter stats.
    """
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Usage (Auto-Estimated Metrics)")
    print("="*80)

    # Note: In real usage, you'd call:
    # from split_task import split_backlog_tasks
    # result = split_backlog_tasks(project_id=10405, tenant="sliit")

    # For this example, we'll simulate the result
    simulated_result = {
        "success": True,
        "items_processed": 10,
        "subtasks_created": 32,
        "filter_stats": {
            'total_candidates': 100,
            'accepted': 60,
            'rejected_quality': 22,
            'rejected_duplicate': 18
        },
        "duplicate_stats": {
            'duplicates_detected': 8,
            'total_generated': 1000
        },
        "evaluation_metrics": {
            "precision": 0.885,
            "recall": 0.842,
            "f1_score": 0.863,
            "acceptance_rate": 0.60,
            "quality_rejection_rate": 0.22,
            "duplicate_rejection_rate": 0.18,
            "duplicate_rate": 0.008
        },
        "evaluation_report": "[Full formatted report here]"
    }

    # Access metrics
    metrics = simulated_result['evaluation_metrics']

    print("\nKey Metrics:")
    print(f"  Precision:  {metrics['precision']*100:.2f}% (target: 88.5%)")
    print(f"  Recall:     {metrics['recall']*100:.2f}% (target: 84.2%)")
    print(f"  F1-Score:   {metrics['f1_score']*100:.2f}% (target: 86.3%)")

    print("\nQuality Filters:")
    print(f"  Acceptance Rate:        {metrics['acceptance_rate']*100:.2f}% (target: 60%)")
    print(f"  Quality Rejection Rate: {metrics['quality_rejection_rate']*100:.2f}% (target: 22%)")
    print(f"  Duplicate Rejection:    {metrics['duplicate_rejection_rate']*100:.2f}% (target: 18%)")

    print("\nDuplicate Detection:")
    print(f"  Duplicate Rate: {metrics['duplicate_rate']*100:.2f}%")
    print(f"  Status: BETTER than human baseline (2.1%)")

    print("\nFull Report:")
    print(simulated_result['evaluation_report'])


# ============================================================================
# PATTERN 2: Advanced Usage (With Expert Baseline)
# ============================================================================

def example_2_with_expert_baseline():
    """
    For highest accuracy, provide expert-identified subtasks.

    Expert baseline should be a list of subtask summaries that 2-3 senior
    developers would identify as required work items.
    """
    print("\n" + "="*80)
    print("EXAMPLE 2: With Expert Baseline (True Accuracy)")
    print("="*80)

    # Define what 3 experts would identify as required subtasks
    expert_baseline = [
        "Implement JWT token validation",
        "Set up OAuth2 provider integration",
        "Configure session expiry timeout",
        "Add password reset functionality",
        "Create unit tests for auth module",
        "Write integration tests",
        "Document API endpoints",
        "Add error handling",
        "Implement rate limiting",
        "Add logging",
    ]

    # What the NLP system actually generated
    generated_subtasks = [
        "Implement JWT token validation",  # TP
        "Set up OAuth2 provider integration",  # TP
        "Configure session timeouts",  # TP (paraphrase match)
        "Add password reset feature",  # TP (partial match)
        "Create unit tests for auth module",  # TP
        "Write integration tests for security",  # TP (partial match)
        "Document API endpoints and responses",  # TP (partial match)
        "Test error handling scenarios",  # TP (partial match)
        "Validate user input on login form",  # FP (not in baseline)
        "Add audit logging for security",  # FP (partial match, counts as FP)
    ]

    # Initialize evaluator
    evaluator = TaskSplittingEvaluator()

    # Evaluate
    eval_result = evaluator.evaluate_generated_subtasks(
        generated_subtasks,
        expert_baseline
    )

    print("\nComparison:")
    print(f"  Expert baseline:    {len(expert_baseline)} subtasks")
    print(f"  System generated:   {len(generated_subtasks)} subtasks")
    print(f"  True positives:     {eval_result['true_positives']}")
    print(f"  False positives:    {eval_result['false_positives']}")
    print(f"  False negatives:    {eval_result['false_negatives']}")

    print("\nAccuracy Metrics:")
    print(f"  Precision: {eval_result['precision']*100:.2f}% (target: 88.5%)")
    print(f"  Recall:    {eval_result['recall']*100:.2f}% (target: 84.2%)")
    print(f"  F1-Score:  {eval_result['f1_score']*100:.2f}% (target: 86.3%)")

    # Interpretation
    print("\nInterpretation:")
    if eval_result['precision'] >= 0.885:
        print("  ✓ Precision is good - most generated subtasks are valid")
    else:
        print("  ✗ Precision below target - too many false positives")
        print("    Action: Increase quality threshold or review NLP filters")

    if eval_result['recall'] >= 0.842:
        print("  ✓ Recall is good - system catches most required subtasks")
    else:
        print("  ✗ Recall below target - missing important subtasks")
        print("    Action: Expand keyword dictionary, add training data")


# ============================================================================
# PATTERN 3: Custom Evaluation (Direct API Usage)
# ============================================================================

def example_3_custom_evaluation():
    """
    Direct API usage for more control over evaluation.

    Useful for:
    - Evaluating multiple aspects separately
    - Custom thresholds
    - Integration with other tools
    """
    print("\n" + "="*80)
    print("EXAMPLE 3: Custom Evaluation (Direct API)")
    print("="*80)

    evaluator = TaskSplittingEvaluator()

    # --------
    # Scenario: Evaluate a specific project run
    # --------

    print("\n1. SUBTASK QUALITY")
    print("-" * 40)

    generated = [
        "Fix authentication bug",
        "Update password validation",
        "Implement 2FA feature",
        "Add email verification",
        "Test password reset flow",
        "Document password policy"
    ]

    expert = [
        "Fix authentication bug",
        "Update password validation",
        "Implement 2FA feature",
        "Add email verification",
        "Test password reset",
        "Document security policy"
    ]

    result_quality = evaluator.evaluate_generated_subtasks(generated, expert)

    print(f"  Generated: {len(generated)}, Expert: {len(expert)}")
    print(f"  Precision: {result_quality['precision']*100:.2f}%")
    print(f"  Recall:    {result_quality['recall']*100:.2f}%")
    print(f"  F1-Score:  {result_quality['f1_score']*100:.2f}%")

    # --------
    print("\n2. TAG PREDICTION QUALITY")
    print("-" * 40)

    predicted_tags = [
        ['backend', 'security'],
        ['validation'],
        ['feature'],
        ['email'],
        ['testing'],
        ['documentation']
    ]

    actual_tags = [
        ['backend', 'security', 'authentication'],
        ['validation', 'password'],
        ['feature', 'enhancement'],
        ['email', 'notification'],
        ['testing', 'qa'],
        ['documentation', 'security-policy']
    ]

    result_tags = evaluator.evaluate_tag_predictions(predicted_tags, actual_tags)

    print(f"  Predictions: {result_tags['total_predictions']}")
    print(f"  Correct:     {result_tags['correct_predictions']}")
    print(f"  Accuracy:    {result_tags['accuracy']*100:.2f}% (target: 91.4%)")

    # --------
    print("\n3. DUPLICATE DETECTION")
    print("-" * 40)

    result_dup = evaluator.evaluate_duplicate_rate(
        duplicates_detected=8,
        total_generated=1000
    )

    print(f"  Total generated:  1000")
    print(f"  Duplicates found: 8")
    print(f"  Rate:             {result_dup['duplicate_rate']*100:.2f}%")
    print(f"  vs Human:         2.1% (system is better: {result_dup['beats_human']})")

    # --------
    print("\n4. FILTER EFFECTIVENESS")
    print("-" * 40)

    result_filters = evaluator.evaluate_acceptance_rate(
        accepted_count=60,
        rejected_quality=22,
        rejected_duplicate=18,
        total_candidates=100
    )

    print(f"  Total candidates: 100")
    print(f"  Accepted:         {result_filters['counts']['accepted']} ({result_filters['acceptance_rate']*100:.2f}%)")
    print(f"  Quality rejected: {result_filters['counts']['rejected_quality']} ({result_filters['quality_rejection_rate']*100:.2f}%)")
    print(f"  Duplicate rej:    {result_filters['counts']['rejected_duplicate']} ({result_filters['duplicate_rejection_rate']*100:.2f}%)")


# ============================================================================
# PATTERN 4: Monitoring Over Time
# ============================================================================

def example_4_monitoring():
    """
    Track metrics across multiple runs to identify trends.
    """
    print("\n" + "="*80)
    print("EXAMPLE 4: Monitoring Metrics Over Time")
    print("="*80)

    # Simulate 5 consecutive project runs
    runs = [
        {"date": "2026-04-22", "project": 10404, "precision": 0.842, "recall": 0.820, "f1": 0.831},
        {"date": "2026-04-23", "project": 10405, "precision": 0.863, "recall": 0.835, "f1": 0.849},
        {"date": "2026-04-24", "project": 10406, "precision": 0.878, "recall": 0.842, "f1": 0.860},
        {"date": "2026-04-25", "project": 10408, "precision": 0.885, "recall": 0.840, "f1": 0.862},
        {"date": "2026-04-26", "project": 10237, "precision": 0.890, "recall": 0.845, "f1": 0.867},
    ]

    print("\nRun Summary:")
    print("Date       | Project | Precision | Recall | F1-Score | Status")
    print("-" * 62)

    target_precision = 0.885
    target_recall = 0.842
    target_f1 = 0.863

    for run in runs:
        prec = run['precision']
        rec = run['recall']
        f1 = run['f1']

        status = "✓" if (prec >= target_precision and rec >= target_recall) else "~"

        print(f"{run['date']} | {run['project']} | {prec*100:.2f}%     | {rec*100:.2f}% | {f1*100:.2f}%   | {status}")

    # Calculate trends
    precisions = [r['precision'] for r in runs]
    recalls = [r['recall'] for r in runs]
    f1s = [r['f1'] for r in runs]

    prec_trend = precisions[-1] - precisions[0]
    rec_trend = recalls[-1] - recalls[0]
    f1_trend = f1s[-1] - f1s[0]

    print("\nTrends (first to last run):")
    print(f"  Precision: {prec_trend:+.2%} {'↑ Improving' if prec_trend > 0 else '↓ Declining'}")
    print(f"  Recall:    {rec_trend:+.2%} {'↑ Improving' if rec_trend > 0 else '↓ Declining'}")
    print(f"  F1-Score:  {f1_trend:+.2%} {'↑ Improving' if f1_trend > 0 else '↓ Declining'}")

    print("\nConclusion:")
    if prec_trend > 0 and rec_trend > 0:
        print("  ✓ System is improving across all metrics!")
    else:
        print("  ! Some metrics declining - investigate potential issues")


# ============================================================================
# PATTERN 5: Integration with Logging
# ============================================================================

def example_5_logging_integration():
    """
    How evaluation metrics integrate with system logging.
    """
    print("\n" + "="*80)
    print("EXAMPLE 5: Logging Integration")
    print("="*80)

    print("\nLog output from split_backlog_tasks():")
    print("-" * 80)

    log_output = """
    INFO: Initializing ML models...
    INFO: ML models loaded from disk
    INFO: Skipping task 10406-3 because it is a Bug
    INFO: Subtask 10406-1-SUB-1 skipped: low quality score (0.18 < 0.25)
    INFO: Subtask 10406-2-SUB-3 skipped: duplicate (similarity: 0.75)
    INFO: Subtask 10406-1-SUB-2: Tag confidence=High, Quality=Good
    INFO: Task splitting complete: 32 subtasks created
    INFO: Overall confidence: High (0.76)
    INFO: Average quality: 0.63
    INFO: ML models used: True

    ================================================================================
    TASK SPLITTING EVALUATION REPORT
    ================================================================================

    PRIMARY METRICS (Precision, Recall, F1):
      Precision:  88.42% (target: 88.5%)
      Recall:     84.00% (target: 84.2%)
      F1-Score:   86.15% (target: 86.3%)

    TAG PREDICTION:
      Accuracy:   90.00% (target: 91.4%)

    DUPLICATE DETECTION:
      Rate:       0.80% (target: 0.8%)
      Baseline:   2.1% (human experts)
      [YES] Beats human baseline by 1.30pp

    QUALITY FILTERS:
      Acceptance: 60.00% (target: 60%)
      Quality Rejection: 22.00% (target: 22%)
      Duplicate Rejection: 18.00% (target: 18%)

    ================================================================================
    """

    print(log_output)


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("\n")
    print("╔" + "═"*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "TASK SPLITTING EVALUATION METRICS - USAGE EXAMPLES".center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "═"*78 + "╝")

    example_1_basic_usage()
    example_2_with_expert_baseline()
    example_3_custom_evaluation()
    example_4_monitoring()
    example_5_logging_integration()

    print("\n" + "="*80)
    print("For more details, see EVALUATION_GUIDE.md")
    print("="*80 + "\n")
