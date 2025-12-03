"""
Classifier Agent Prompts Package
"""

from .classifier_prompts import (
    TICKET_CATEGORIES,
    CLASSIFIER_SYSTEM_PROMPT,
    CLASSIFIER_USER_TEMPLATE,
    get_classifier_prompt,
)

__all__ = [
    "TICKET_CATEGORIES",
    "CLASSIFIER_SYSTEM_PROMPT",
    "CLASSIFIER_USER_TEMPLATE",
    "get_classifier_prompt",
]
