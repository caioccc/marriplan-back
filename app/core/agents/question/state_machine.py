"""
Question State Machine for managing question interaction flows.
"""
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
import logging

logger = logging.getLogger(__name__)


class QuestionState(Enum):
    """States for question interaction flow."""
    NO_QUESTION = "no_question"                    # No active question
    QUESTION_PRESENTED = "question_presented"      # Question has been shown to user
    WAITING_ANSWER = "waiting_answer"              # Waiting for user's answer
    ANSWER_GIVEN = "answer_given"                  # User has provided an answer
    EXPLANATION_SHOWN = "explanation_shown"        # Explanation has been displayed
    QUESTION_COMPLETED = "question_completed"      # Question cycle completed
    ERROR_STATE = "error_state"                    # Error occurred during process


class QuestionEvent(Enum):
    """Events that trigger state transitions."""
    PRESENT_QUESTION = "present_question"          # Show question to user
    RECEIVE_ANSWER = "receive_answer"              # User provides answer
    SHOW_EXPLANATION = "show_explanation"          # Display explanation
    COMPLETE_QUESTION = "complete_question"        # Mark question as done
    RESET_SESSION = "reset_session"                # Reset to initial state
    ERROR_OCCURRED = "error_occurred"              # Handle error
    REQUEST_HINT = "request_hint"                  # User requests hint
    REQUEST_NEW_QUESTION = "request_new_question"  # User wants new question


@dataclass
class QuestionContext:
    """Context data for question state machine."""
    question_id: Optional[str] = None
    question_data: Optional[Dict[str, Any]] = None
    user_answer: Optional[str] = None
    correct_answer: Optional[str] = None
    is_correct: Optional[bool] = None
    time_started: Optional[datetime] = None
    time_answered: Optional[datetime] = None
    hints_shown: int = 0
    explanation_data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_time_spent(self) -> Optional[int]:
        """Get time spent on question in seconds."""
        if self.time_started and self.time_answered:
            return int((self.time_answered - self.time_started).total_seconds())
        return None
    
    def reset(self):
        """Reset context for new question."""
        self.question_id = None
        self.question_data = None
        self.user_answer = None
        self.correct_answer = None
        self.is_correct = None
        self.time_started = None
        self.time_answered = None
        self.hints_shown = 0
        self.explanation_data = None
        self.metadata.clear()


@dataclass
class StateTransition:
    """Represents a state transition in the machine."""
    from_state: QuestionState
    event: QuestionEvent
    to_state: QuestionState
    condition: Optional[Callable[[QuestionContext], bool]] = None
    action: Optional[Callable[[QuestionContext], None]] = None


class QuestionStateMachine:
    """State machine for managing question interaction flows."""
    
    def __init__(self):
        """Initialize the state machine with transitions."""
        self.current_state = QuestionState.NO_QUESTION
        self.context = QuestionContext()
        
        # Define state transitions
        self.transitions = self._build_transitions()
        
        # State entry/exit actions
        self.entry_actions = self._build_entry_actions()
        self.exit_actions = self._build_exit_actions()
        
        # Event handlers
        self.event_handlers = self._build_event_handlers()
        
        logger.info("Question state machine initialized")
    
    def _build_transitions(self) -> List[StateTransition]:
        """Build the complete state transition table."""
        return [
            # From NO_QUESTION
            StateTransition(
                QuestionState.NO_QUESTION,
                QuestionEvent.PRESENT_QUESTION,
                QuestionState.QUESTION_PRESENTED,
                action=self._action_present_question
            ),
            
            # From QUESTION_PRESENTED
            StateTransition(
                QuestionState.QUESTION_PRESENTED,
                QuestionEvent.RECEIVE_ANSWER,
                QuestionState.ANSWER_GIVEN,
                action=self._action_process_answer
            ),
            StateTransition(
                QuestionState.QUESTION_PRESENTED,
                QuestionEvent.REQUEST_HINT,
                QuestionState.WAITING_ANSWER,
                action=self._action_show_hint
            ),
            StateTransition(
                QuestionState.QUESTION_PRESENTED,
                QuestionEvent.REQUEST_NEW_QUESTION,
                QuestionState.NO_QUESTION,
                action=self._action_reset_context
            ),
            
            # From WAITING_ANSWER
            StateTransition(
                QuestionState.WAITING_ANSWER,
                QuestionEvent.RECEIVE_ANSWER,
                QuestionState.ANSWER_GIVEN,
                action=self._action_process_answer
            ),
            StateTransition(
                QuestionState.WAITING_ANSWER,
                QuestionEvent.REQUEST_HINT,
                QuestionState.WAITING_ANSWER,
                action=self._action_show_hint
            ),
            
            # From ANSWER_GIVEN
            StateTransition(
                QuestionState.ANSWER_GIVEN,
                QuestionEvent.SHOW_EXPLANATION,
                QuestionState.EXPLANATION_SHOWN,
                action=self._action_show_explanation
            ),
            StateTransition(
                QuestionState.ANSWER_GIVEN,
                QuestionEvent.COMPLETE_QUESTION,
                QuestionState.QUESTION_COMPLETED,
                action=self._action_complete_question
            ),
            
            # From EXPLANATION_SHOWN
            StateTransition(
                QuestionState.EXPLANATION_SHOWN,
                QuestionEvent.COMPLETE_QUESTION,
                QuestionState.QUESTION_COMPLETED,
                action=self._action_complete_question
            ),
            StateTransition(
                QuestionState.EXPLANATION_SHOWN,
                QuestionEvent.REQUEST_NEW_QUESTION,
                QuestionState.NO_QUESTION,
                action=self._action_reset_context
            ),
            
            # From QUESTION_COMPLETED
            StateTransition(
                QuestionState.QUESTION_COMPLETED,
                QuestionEvent.REQUEST_NEW_QUESTION,
                QuestionState.NO_QUESTION,
                action=self._action_reset_context
            ),
            StateTransition(
                QuestionState.QUESTION_COMPLETED,
                QuestionEvent.PRESENT_QUESTION,
                QuestionState.QUESTION_PRESENTED,
                action=self._action_present_question
            ),
            
            # Error handling from any state
            StateTransition(
                QuestionState.NO_QUESTION,
                QuestionEvent.ERROR_OCCURRED,
                QuestionState.ERROR_STATE,
                action=self._action_handle_error
            ),
            StateTransition(
                QuestionState.QUESTION_PRESENTED,
                QuestionEvent.ERROR_OCCURRED,
                QuestionState.ERROR_STATE,
                action=self._action_handle_error
            ),
            StateTransition(
                QuestionState.WAITING_ANSWER,
                QuestionEvent.ERROR_OCCURRED,
                QuestionState.ERROR_STATE,
                action=self._action_handle_error
            ),
            StateTransition(
                QuestionState.ANSWER_GIVEN,
                QuestionEvent.ERROR_OCCURRED,
                QuestionState.ERROR_STATE,
                action=self._action_handle_error
            ),
            StateTransition(
                QuestionState.EXPLANATION_SHOWN,
                QuestionEvent.ERROR_OCCURRED,
                QuestionState.ERROR_STATE,
                action=self._action_handle_error
            ),
            
            # Reset from error state
            StateTransition(
                QuestionState.ERROR_STATE,
                QuestionEvent.RESET_SESSION,
                QuestionState.NO_QUESTION,
                action=self._action_reset_context
            ),
            
            # Global reset
            StateTransition(
                QuestionState.QUESTION_PRESENTED,
                QuestionEvent.RESET_SESSION,
                QuestionState.NO_QUESTION,
                action=self._action_reset_context
            ),
            StateTransition(
                QuestionState.WAITING_ANSWER,
                QuestionEvent.RESET_SESSION,
                QuestionState.NO_QUESTION,
                action=self._action_reset_context
            ),
            StateTransition(
                QuestionState.ANSWER_GIVEN,
                QuestionEvent.RESET_SESSION,
                QuestionState.NO_QUESTION,
                action=self._action_reset_context
            ),
            StateTransition(
                QuestionState.EXPLANATION_SHOWN,
                QuestionEvent.RESET_SESSION,
                QuestionState.NO_QUESTION,
                action=self._action_reset_context
            ),
        ]
    
    def _build_entry_actions(self) -> Dict[QuestionState, Callable]:
        """Build entry actions for each state."""
        return {
            QuestionState.QUESTION_PRESENTED: self._on_enter_question_presented,
            QuestionState.WAITING_ANSWER: self._on_enter_waiting_answer,
            QuestionState.ANSWER_GIVEN: self._on_enter_answer_given,
            QuestionState.EXPLANATION_SHOWN: self._on_enter_explanation_shown,
            QuestionState.QUESTION_COMPLETED: self._on_enter_question_completed,
            QuestionState.ERROR_STATE: self._on_enter_error_state,
        }
    
    def _build_exit_actions(self) -> Dict[QuestionState, Callable]:
        """Build exit actions for each state."""
        return {
            QuestionState.QUESTION_PRESENTED: self._on_exit_question_presented,
            QuestionState.ANSWER_GIVEN: self._on_exit_answer_given,
        }
    
    def _build_event_handlers(self) -> Dict[QuestionEvent, Callable]:
        """Build event-specific handlers."""
        return {
            QuestionEvent.PRESENT_QUESTION: self._handle_present_question,
            QuestionEvent.RECEIVE_ANSWER: self._handle_receive_answer,
            QuestionEvent.SHOW_EXPLANATION: self._handle_show_explanation,
            QuestionEvent.REQUEST_HINT: self._handle_request_hint,
            QuestionEvent.REQUEST_NEW_QUESTION: self._handle_request_new_question,
            QuestionEvent.ERROR_OCCURRED: self._handle_error_occurred,
        }
    
    def trigger_event(self, event: QuestionEvent, **kwargs) -> bool:
        """
        Trigger an event and execute the corresponding state transition.
        
        Args:
            event: The event to trigger
            **kwargs: Additional data for the event
            
        Returns:
            bool: True if transition was successful, False otherwise
        """
        try:
            # Find valid transition
            transition = self._find_transition(self.current_state, event)
            if not transition:
                logger.warning(f"No transition found for event {event.value} from state {self.current_state.value}")
                return False
            
            # Check condition if exists
            if transition.condition and not transition.condition(self.context):
                logger.warning(f"Transition condition failed for {event.value}")
                return False
            
            # Update context with event data
            for key, value in kwargs.items():
                setattr(self.context, key, value)
            
            # Execute exit action for current state
            if self.current_state in self.exit_actions:
                self.exit_actions[self.current_state](self.context)
            
            # Execute transition action
            if transition.action:
                transition.action(self.context)
            
            # Change state
            old_state = self.current_state
            self.current_state = transition.to_state
            
            # Execute entry action for new state
            if self.current_state in self.entry_actions:
                self.entry_actions[self.current_state](self.context)
            
            logger.info(f"State transition: {old_state.value} -> {self.current_state.value} (event: {event.value})")
            return True
            
        except Exception as e:
            logger.error(f"Error during state transition: {e}")
            self.current_state = QuestionState.ERROR_STATE
            return False
    
    def _find_transition(self, from_state: QuestionState, event: QuestionEvent) -> Optional[StateTransition]:
        """Find a valid transition for the given state and event."""
        for transition in self.transitions:
            if transition.from_state == from_state and transition.event == event:
                return transition
        return None
    
    def get_valid_events(self) -> List[QuestionEvent]:
        """Get list of valid events for current state."""
        valid_events = []
        for transition in self.transitions:
            if transition.from_state == self.current_state:
                valid_events.append(transition.event)
        return valid_events
    
    def is_valid_event(self, event: QuestionEvent) -> bool:
        """Check if an event is valid for current state."""
        return event in self.get_valid_events()
    
    def reset(self):
        """Reset state machine to initial state."""
        self.current_state = QuestionState.NO_QUESTION
        self.context.reset()
        logger.info("State machine reset to initial state")
    
    # Action methods
    def _action_present_question(self, context: QuestionContext):
        """Action for presenting a question."""
        context.time_started = datetime.now()
        context.hints_shown = 0
        logger.debug(f"Question {context.question_id} presented at {context.time_started}")
    
    def _action_process_answer(self, context: QuestionContext):
        """Action for processing user's answer."""
        context.time_answered = datetime.now()
        if context.question_data and context.user_answer:
            context.correct_answer = context.question_data.get('correct_choice', '').upper()
            context.is_correct = context.user_answer.upper() == context.correct_answer
        logger.debug(f"Answer processed: {context.user_answer}, correct: {context.is_correct}")
    
    def _action_show_explanation(self, context: QuestionContext):
        """Action for showing explanation."""
        if context.question_data:
            context.explanation_data = context.question_data.get('explanation', {})
        logger.debug("Explanation prepared for display")
    
    def _action_show_hint(self, context: QuestionContext):
        """Action for showing a hint."""
        context.hints_shown += 1
        logger.debug(f"Hint shown (total: {context.hints_shown})")
    
    def _action_complete_question(self, context: QuestionContext):
        """Action for completing a question."""
        context.metadata['completed_at'] = datetime.now()
        context.metadata['total_time'] = context.get_time_spent()
        logger.debug(f"Question {context.question_id} completed")
    
    def _action_reset_context(self, context: QuestionContext):
        """Action for resetting context."""
        old_question_id = context.question_id
        context.reset()
        logger.debug(f"Context reset (previous question: {old_question_id})")
    
    def _action_handle_error(self, context: QuestionContext):
        """Action for handling errors."""
        context.metadata['error_timestamp'] = datetime.now()
        context.metadata['error_state'] = self.current_state.value
        logger.error("Error state entered")
    
    # Entry actions
    def _on_enter_question_presented(self, context: QuestionContext):
        """Called when entering QUESTION_PRESENTED state."""
        pass
    
    def _on_enter_waiting_answer(self, context: QuestionContext):
        """Called when entering WAITING_ANSWER state."""
        pass
    
    def _on_enter_answer_given(self, context: QuestionContext):
        """Called when entering ANSWER_GIVEN state."""
        pass
    
    def _on_enter_explanation_shown(self, context: QuestionContext):
        """Called when entering EXPLANATION_SHOWN state."""
        pass
    
    def _on_enter_question_completed(self, context: QuestionContext):
        """Called when entering QUESTION_COMPLETED state."""
        pass
    
    def _on_enter_error_state(self, context: QuestionContext):
        """Called when entering ERROR_STATE."""
        pass
    
    # Exit actions
    def _on_exit_question_presented(self, context: QuestionContext):
        """Called when exiting QUESTION_PRESENTED state."""
        pass
    
    def _on_exit_answer_given(self, context: QuestionContext):
        """Called when exiting ANSWER_GIVEN state."""
        pass
    
    # Event handlers
    def _handle_present_question(self, context: QuestionContext):
        """Handle PRESENT_QUESTION event."""
        pass
    
    def _handle_receive_answer(self, context: QuestionContext):
        """Handle RECEIVE_ANSWER event."""
        pass
    
    def _handle_show_explanation(self, context: QuestionContext):
        """Handle SHOW_EXPLANATION event."""
        pass
    
    def _handle_request_hint(self, context: QuestionContext):
        """Handle REQUEST_HINT event."""
        pass
    
    def _handle_request_new_question(self, context: QuestionContext):
        """Handle REQUEST_NEW_QUESTION event."""
        pass
    
    def _handle_error_occurred(self, context: QuestionContext):
        """Handle ERROR_OCCURRED event."""
        pass
    
    def get_state_info(self) -> Dict[str, Any]:
        """Get current state machine information."""
        return {
            'current_state': self.current_state.value,
            'valid_events': [event.value for event in self.get_valid_events()],
            'context': {
                'question_id': self.context.question_id,
                'has_question_data': self.context.question_data is not None,
                'user_answer': self.context.user_answer,
                'is_correct': self.context.is_correct,
                'hints_shown': self.context.hints_shown,
                'time_spent': self.context.get_time_spent(),
            }
        }