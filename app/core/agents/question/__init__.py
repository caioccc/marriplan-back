"""
Question Agent module for managing complete question workflows.

This module provides a comprehensive question management system with:
- State machine for question interaction flows
- Advanced question formatting for different contexts
- Reference resolution for study materials
- Complete agent implementation for orchestration

Components:
- QuestionAgent: Main agent for question management
- QuestionStateMachine: State management for question workflows
- QuestionFormatter: Advanced formatting for different presentation contexts
- ReferenceResolver: Resolution of study materials and references
"""

from .question_agent import QuestionAgent
from .state_machine import (
    QuestionStateMachine, 
    QuestionState, 
    QuestionEvent, 
    QuestionContext
)
from .question_formatter import (
    QuestionFormatter, 
    QuestionFormat, 
    FormattedQuestion
)
from .reference_resolver import (
    ReferenceResolver, 
    ReferenceType, 
    ResolvedReference, 
    ReferenceContext
)

__all__ = [
    # Main agent
    'QuestionAgent',
    
    # State machine
    'QuestionStateMachine',
    'QuestionState',
    'QuestionEvent', 
    'QuestionContext',
    
    # Formatter
    'QuestionFormatter',
    'QuestionFormat',
    'FormattedQuestion',
    
    # Reference resolver
    'ReferenceResolver',
    'ReferenceType',
    'ResolvedReference',
    'ReferenceContext',
]