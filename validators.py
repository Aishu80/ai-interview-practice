"""
Input validation utilities for the AI Interview Practice platform.

Provides validation functions for:
- Uploaded resume and profile files (.pdf, .docx, .txt)
- Generated Multiple Choice Question (MCQ) sets
- Interview configuration settings
- User written responses
- General text sanitization
"""

import os
import re
from typing import List, Tuple, Dict, Any, Union
from models.schemas import InterviewType, ExperienceLevel, DifficultyMode, Difficulty, MCQuestion
from utils.config import get_config


ALLOWED_FILE_EXTENSIONS = {".pdf", ".docx", ".txt"}


def validate_file(file_path: str, max_size_bytes: int) -> tuple[bool, str]:
    """Validates an uploaded file path for existence, type, and size constraints.

    Checks:
    1. File path is non-empty and points to an existing regular file.
    2. File extension is supported (.pdf, .docx, .txt).
    3. File is not empty (size > 0 bytes).
    4. File size does not exceed max_size_bytes.

    Args:
        file_path: Path to the target file on the local file system.
        max_size_bytes: Maximum allowed file size in bytes.

    Returns:
        tuple[bool, str]: A tuple of (is_valid, error_message).
                          If valid, error_message is an empty string.
    """
    try:
        if not file_path or not isinstance(file_path, str):
            return False, "File path must be a non-empty string."

        clean_path = file_path.strip()
        if not clean_path:
            return False, "File path cannot be empty or blank."

        if not os.path.exists(clean_path):
            return False, f"File not found: '{clean_path}'."

        if not os.path.isfile(clean_path):
            return False, f"Specified path is not a regular file: '{clean_path}'."

        # Extension check
        ext = os.path.splitext(clean_path)[1].lower()
        if ext not in ALLOWED_FILE_EXTENSIONS:
            allowed_str = ", ".join(sorted(ALLOWED_FILE_EXTENSIONS))
            return False, f"Unsupported file extension '{ext}'. Allowed extensions are: {allowed_str}."

        # Size check
        size = os.path.getsize(clean_path)
        if size == 0:
            return False, "File is empty (0 bytes)."

        if size > max_size_bytes:
            size_mb = size / (1024 * 1024)
            max_mb = max_size_bytes / (1024 * 1024)
            return (
                False,
                f"File size ({size_mb:.2f} MB) exceeds the maximum allowed size ({max_mb:.2f} MB).",
            )

        return True, ""
    except Exception as exc:
        return False, f"Unexpected error while validating file: {str(exc)}"


def validate_mcq_set(questions: list) -> tuple[bool, list[str]]:
    """Validates a set of multiple-choice questions for completeness and structure.

    Checks:
    - Input is a list containing exactly 20 questions.
    - Each question possesses all required fields: id, question_text, options, correct_answer.
    - Each question contains exactly 4 non-empty options.
    - correct_answer is an integer in the range 0 to 3.
    - No duplicate question IDs exist.
    - No duplicate question texts exist.

    Args:
        questions: List of MCQuestion dataclass instances or question dictionaries.

    Returns:
        tuple[bool, list[str]]: (is_valid, errors_list).
    """
    errors: list[str] = []

    try:
        if not isinstance(questions, list):
            return False, ["Questions input must be a list."]

        if len(questions) != 20:
            errors.append(f"MCQ set must contain exactly 20 questions, but received {len(questions)}.")

        seen_ids: set[str] = set()
        seen_texts: set[str] = set()

        for idx, item in enumerate(questions, start=1):
            # Extract fields based on type
            if isinstance(item, MCQuestion):
                q_id = item.id
                q_text = item.question_text
                options = item.options
                correct_ans = item.correct_answer
                explanation = item.explanation
            elif isinstance(item, dict):
                q_id = item.get("id")
                q_text = item.get("question_text")
                options = item.get("options")
                correct_ans = item.get("correct_answer")
                explanation = item.get("explanation")
            else:
                errors.append(f"Question #{idx} is neither an MCQuestion instance nor a dictionary.")
                continue

            # Validate ID
            if not q_id or not str(q_id).strip():
                errors.append(f"Question #{idx} is missing a valid 'id'.")
            else:
                str_id = str(q_id).strip()
                if str_id in seen_ids:
                    errors.append(f"Question #{idx} has duplicate ID '{str_id}'.")
                else:
                    seen_ids.add(str_id)

            # Validate Question Text
            if not q_text or not str(q_text).strip():
                errors.append(f"Question #{idx} is missing 'question_text'.")
            else:
                norm_text = str(q_text).strip().lower()
                if norm_text in seen_texts:
                    errors.append(
                        f"Question #{idx} contains duplicate question text: '{str(q_text)[:50]}...'."
                    )
                else:
                    seen_texts.add(norm_text)

            # Validate Options
            if not isinstance(options, list):
                errors.append(f"Question #{idx} 'options' must be a list.")
            elif len(options) != 4:
                errors.append(f"Question #{idx} must have exactly 4 options, found {len(options)}.")
            else:
                for opt_i, opt in enumerate(options):
                    if not isinstance(opt, str) or not opt.strip():
                        errors.append(f"Question #{idx} has an empty option at index {opt_i}.")

            # Validate Correct Answer
            if not isinstance(correct_ans, int) or isinstance(correct_ans, bool):
                errors.append(
                    f"Question #{idx} 'correct_answer' must be an integer index (0-3), got {type(correct_ans).__name__}."
                )
            elif correct_ans not in (0, 1, 2, 3):
                errors.append(
                    f"Question #{idx} 'correct_answer' index {correct_ans} is out of bounds (must be 0, 1, 2, or 3)."
                )

        return len(errors) == 0, errors

    except Exception as exc:
        return False, [f"Unexpected error during MCQ set validation: {str(exc)}"]


def validate_interview_config(config: dict) -> tuple[bool, list[str]]:
    """Validates interview configuration settings.

    Checks:
    - target_role is not empty.
    - interview_type is a valid InterviewType enum value.
    - experience_level is a valid ExperienceLevel enum value.
    - difficulty_mode is a valid DifficultyMode enum value.

    Args:
        config: Configuration dictionary (or object with get / attribute access).

    Returns:
        tuple[bool, list[str]]: (is_valid, errors_list).
    """
    errors: list[str] = []

    try:
        if not isinstance(config, dict):
            # Check if it has to_dict or is an InterviewConfig dataclass
            if hasattr(config, "to_dict") and callable(config.to_dict):
                config = config.to_dict()
            elif hasattr(config, "__dict__"):
                config = vars(config)
            else:
                return False, ["Interview configuration must be a dictionary or InterviewConfig instance."]

        # target_role validation
        target_role = config.get("target_role", "")
        if not target_role or not str(target_role).strip():
            errors.append("Target role cannot be blank or empty.")

        # interview_type validation
        valid_interview_types = {e.value for e in InterviewType}
        interview_type = str(config.get("interview_type", "")).strip().lower()
        if interview_type not in valid_interview_types:
            allowed = ", ".join(sorted(valid_interview_types))
            errors.append(
                f"Invalid interview type '{interview_type}'. Allowed types are: {allowed}."
            )

        # experience_level validation
        valid_experience_levels = {e.value for e in ExperienceLevel}
        experience_level = str(config.get("experience_level", "")).strip().lower()
        if experience_level not in valid_experience_levels:
            allowed = ", ".join(sorted(valid_experience_levels))
            errors.append(
                f"Invalid experience level '{experience_level}'. Allowed levels are: {allowed}."
            )

        # difficulty_mode validation
        valid_difficulty_modes = {e.value for e in DifficultyMode}
        difficulty_mode = str(config.get("difficulty_mode", "")).strip().lower()
        if difficulty_mode not in valid_difficulty_modes:
            allowed = ", ".join(sorted(valid_difficulty_modes))
            errors.append(
                f"Invalid difficulty mode '{difficulty_mode}'. Allowed modes are: {allowed}."
            )

        return len(errors) == 0, errors

    except Exception as exc:
        return False, [f"Unexpected error during configuration validation: {str(exc)}"]


def validate_written_answer(answer: str) -> tuple[bool, str]:
    """Validates that a candidate's written answer is not blank or whitespace-only.

    Args:
        answer: Candidate response string.

    Returns:
        tuple[bool, str]: (is_valid, error_message). If valid, error_message is empty.
    """
    try:
        if not isinstance(answer, str):
            return False, "Answer must be a text string."

        if not answer.strip():
            return False, "Answer cannot be blank or whitespace-only."

        return True, ""
    except Exception as exc:
        return False, f"Unexpected error during answer validation: {str(exc)}"


def sanitize_text(text: str) -> str:
    """Sanitizes text for safe rendering and processing.

    Operations:
    - Replaces null bytes.
    - Normalizes line endings (CRLF / CR -> LF).
    - Removes unprintable control characters while preserving newlines and tabs.
    - Strips leading and trailing whitespace.

    Args:
        text: Raw text string.

    Returns:
        str: Cleaned and sanitized string.
    """
    if text is None:
        return ""

    try:
        cleaned = str(text)
        # Remove null characters
        cleaned = cleaned.replace("\x00", "")
        # Normalize newlines
        cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
        # Strip ASCII control characters except newline (\x0a) and tab (\x09)
        cleaned = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", cleaned)
        return cleaned.strip()
    except Exception:
        return str(text).strip()
