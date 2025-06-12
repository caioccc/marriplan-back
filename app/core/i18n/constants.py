"""
Constants for internationalization.
"""

from enum import Enum


class SupportedLanguages(Enum):
    """Supported languages for the system."""
    PORTUGUESE = "pt"
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"


class MessageTypes(Enum):
    """Types of messages that can be localized."""
    GREETING = "greeting"
    FAREWELL = "farewell"
    HELP = "help"
    ERROR = "error"
    SUCCESS = "success"
    EXPLANATION = "explanation"
    QUESTION_PROMPT = "question_prompt"
    STUDY_PLAN = "study_plan"
    ENCOURAGEMENT = "encouragement"
    STUDY_TIPS = "study_tips"
    ABOUT_SYSTEM = "about_system"
    CLARIFICATION = "clarification"
    CASUAL = "casual"


class InteractionPatterns(Enum):
    """Types of interaction patterns."""
    GREETING_PATTERN = "greeting_pattern"
    FAREWELL_PATTERN = "farewell_pattern"
    HELP_PATTERN = "help_pattern"
    QUESTION_PATTERN = "question_pattern"
    EXPLANATION_PATTERN = "explanation_pattern"
    AFFIRMATIVE_PATTERN = "affirmative_pattern"
    NEGATIVE_PATTERN = "negative_pattern"
    TECHNICAL_TERMS = "technical_terms"