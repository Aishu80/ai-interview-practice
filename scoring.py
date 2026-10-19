"""
Deterministic scoring functions for the AI Interview Practice platform.

Pure mathematical calculations for:
- MCQ assessment accuracy, difficulty-wise, domain-wise, and topic-wise breakdown
- Written response rubric scoring aggregation
- Combined overall interview scoring (60% MCQ + 40% Written)
- Performance tier categorization
"""

from typing import List, Dict, Any, Optional
from models.schemas import MCQuestion, MCQResults, WrittenAnswerEvaluation, RubricScore


def calculate_mcq_results(
    questions: list[MCQuestion],
    user_answers: dict[str, int],
) -> MCQResults:
    """Calculates comprehensive MCQ scoring metrics based on candidate responses.

    Determines:
    - Overall correct, incorrect, and unanswered counts
    - Overall accuracy percentage
    - Accuracy split by difficulty (Easy, Medium, Hard)
    - Accuracy grouped by domain
    - Accuracy grouped by topic
    - Itemized question details with correctness indicators

    Args:
        questions: List of MCQuestion objects representing the assessment.
        user_answers: Mapping of question ID to the selected option index (0-3).
                      A missing ID or index of -1 denotes an unanswered question.

    Returns:
        MCQResults: Aggregated scoring and analytics dataclass.
    """
    try:
        total_questions = len(questions)
        if total_questions == 0:
            return MCQResults(total_questions=0)

        correct = 0
        incorrect = 0
        unanswered = 0

        easy_total = 0
        easy_correct = 0
        medium_total = 0
        medium_correct = 0
        hard_total = 0
        hard_correct = 0

        domain_stats: dict[str, dict[str, int]] = {}
        topic_stats: dict[str, dict[str, int]] = {}
        question_details: list[dict[str, Any]] = []

        for q in questions:
            # Handle user answer lookup safely
            user_ans = user_answers.get(q.id)
            if user_ans is None and hasattr(q, "id"):
                user_ans = user_answers.get(str(q.id))

            # Determine unanswered status
            if user_ans is None or user_ans < 0:
                is_unanswered = True
                is_correct = False
                unanswered += 1
                selected_option = -1
            else:
                is_unanswered = False
                selected_option = int(user_ans)
                if selected_option == q.correct_answer:
                    is_correct = True
                    correct += 1
                else:
                    is_correct = False
                    incorrect += 1

            # Difficulty tracking
            diff = (q.difficulty or "easy").strip().lower()
            if diff == "easy":
                easy_total += 1
                if is_correct:
                    easy_correct += 1
            elif diff == "medium":
                medium_total += 1
                if is_correct:
                    medium_correct += 1
            elif diff == "hard":
                hard_total += 1
                if is_correct:
                    hard_correct += 1
            else:
                # Default unknown difficulties to easy grouping
                easy_total += 1
                if is_correct:
                    easy_correct += 1

            # Domain tracking
            domain = (q.domain or "General").strip() or "General"
            if domain not in domain_stats:
                domain_stats[domain] = {"total": 0, "correct": 0}
            domain_stats[domain]["total"] += 1
            if is_correct:
                domain_stats[domain]["correct"] += 1

            # Topic tracking
            topic = (q.topic or "General").strip() or "General"
            if topic not in topic_stats:
                topic_stats[topic] = {"total": 0, "correct": 0}
            topic_stats[topic]["total"] += 1
            if is_correct:
                topic_stats[topic]["correct"] += 1

            # Detailed per-question record
            question_details.append({
                "id": q.id,
                "question_text": q.question_text,
                "options": q.options,
                "user_answer": selected_option,
                "correct_answer": q.correct_answer,
                "is_correct": is_correct,
                "is_unanswered": is_unanswered,
                "topic": q.topic,
                "domain": q.domain,
                "difficulty": q.difficulty,
                "explanation": q.explanation,
            })

        # Calculate percentages
        accuracy = round((correct / total_questions) * 100.0, 2)
        easy_accuracy = round((easy_correct / easy_total) * 100.0, 2) if easy_total > 0 else 0.0
        medium_accuracy = (
            round((medium_correct / medium_total) * 100.0, 2) if medium_total > 0 else 0.0
        )
        hard_accuracy = round((hard_correct / hard_total) * 100.0, 2) if hard_total > 0 else 0.0

        # Build domain accuracy dictionary
        domain_accuracy: dict[str, dict[str, Any]] = {}
        for d_name, d_counts in domain_stats.items():
            d_tot = d_counts["total"]
            d_corr = d_counts["correct"]
            domain_accuracy[d_name] = {
                "total": d_tot,
                "correct": d_corr,
                "accuracy": round((d_corr / d_tot) * 100.0, 2) if d_tot > 0 else 0.0,
            }

        # Build topic accuracy dictionary
        topic_accuracy: dict[str, dict[str, Any]] = {}
        for t_name, t_counts in topic_stats.items():
            t_tot = t_counts["total"]
            t_corr = t_counts["correct"]
            topic_accuracy[t_name] = {
                "total": t_tot,
                "correct": t_corr,
                "accuracy": round((t_corr / t_tot) * 100.0, 2) if t_tot > 0 else 0.0,
            }

        return MCQResults(
            total_questions=total_questions,
            correct=correct,
            incorrect=incorrect,
            unanswered=unanswered,
            accuracy=accuracy,
            easy_accuracy=easy_accuracy,
            medium_accuracy=medium_accuracy,
            hard_accuracy=hard_accuracy,
            easy_total=easy_total,
            easy_correct=easy_correct,
            medium_total=medium_total,
            medium_correct=medium_correct,
            hard_total=hard_total,
            hard_correct=hard_correct,
            domain_accuracy=domain_accuracy,
            topic_accuracy=topic_accuracy,
            question_details=question_details,
            total_time=0.0,
        )

    except Exception:
        # Fallback to an empty/safe MCQResults in case of unexpected exceptions
        return MCQResults(total_questions=len(questions) if questions else 0)


def calculate_written_score(evaluations: list[WrittenAnswerEvaluation]) -> float:
    """Calculates the mean rubric score across all written evaluations.

    Extracts individual rubric domain scores from each evaluation. If an evaluation
    contains no individual rubric items, its overall_score is used as fallback.

    Args:
        evaluations: List of WrittenAnswerEvaluation instances.

    Returns:
        float: Arithmetic mean of rubric scores rounded to 2 decimal places, or 0.0 if empty.
    """
    try:
        if not evaluations:
            return 0.0

        scores: list[float] = []

        for evaluation in evaluations:
            if evaluation.rubric_scores:
                for rubric in evaluation.rubric_scores:
                    scores.append(float(rubric.score))
            elif evaluation.overall_score is not None and evaluation.overall_score > 0:
                scores.append(float(evaluation.overall_score))

        if not scores:
            return 0.0

        return round(sum(scores) / len(scores), 2)

    except Exception:
        return 0.0


def calculate_combined_score(
    mcq_accuracy: float,
    written_score: float,
    both_complete: bool,
) -> float | None:
    """Computes the overall weighted score across MCQ and written sections.

    Weighting: 60% MCQ Accuracy + 40% Written Score.
    Returned only if both sections have been completed.

    Args:
        mcq_accuracy: MCQ score / accuracy percentage (0.0 - 100.0).
        written_score: Written assessment mean score (0.0 - 100.0).
        both_complete: True if candidate has completed both stages.

    Returns:
        float | None: Combined score rounded to 2 decimal places, or None if incomplete.
    """
    if not both_complete:
        return None

    try:
        mcq_val = float(mcq_accuracy)
        written_val = float(written_score)
        combined = (mcq_val * 0.60) + (written_val * 0.40)
        return round(combined, 2)
    except (TypeError, ValueError):
        return None


def get_performance_label(score: float) -> str:
    """Maps a numerical score (0-100) to a qualitative performance label.

    Thresholds:
    - >= 90: 'Excellent'
    - >= 75: 'Good'
    - >= 50: 'Average'
    - < 50:  'Needs Improvement'

    Args:
        score: Numerical score from 0.0 to 100.0.

    Returns:
        str: Descriptive performance label.
    """
    try:
        val = float(score)
    except (TypeError, ValueError):
        return "Needs Improvement"

    if val >= 90.0:
        return "Excellent"
    elif val >= 75.0:
        return "Good"
    elif val >= 50.0:
        return "Average"
    else:
        return "Needs Improvement"
