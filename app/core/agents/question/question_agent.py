"""
Question Agent for managing complete question interaction workflows.
"""
from typing import Dict, Any, Optional, List
import logging
import asyncio
from datetime import datetime

from app.core.agents.base import BaseAgent, AgentResponse, AgentCapability
from app.core.models.agent_models import AgentRequest
from app.core.services.intent_detection import IntentType
from app.core.services.question import QuestionService
from app.core.services.search import SearchService

from .state_machine import QuestionStateMachine, QuestionState, QuestionEvent, QuestionContext
from .question_formatter import QuestionFormatter, QuestionFormat
from .reference_resolver import ReferenceResolver, ReferenceContext

logger = logging.getLogger(__name__)


class QuestionAgent(BaseAgent):
    """
    Agent responsible for complete question management workflow.
    
    Handles:
    - Question presentation and formatting
    - Answer validation and feedback
    - State management through question workflow
    - Reference resolution and study materials
    - Hints and explanations
    """
    
    def __init__(self):
        """Initialize the Question Agent."""
        super().__init__(
            name="QuestionAgent",
            capabilities=[
                AgentCapability.QUESTION_MANAGEMENT,
                AgentCapability.QUESTION_HANDLING,
                AgentCapability.ANSWER_VERIFICATION
            ],
            priority=90  # High priority for question-related tasks
        )
        
        # Initialize components
        self.state_machine = QuestionStateMachine()
        self.formatter = QuestionFormatter()
        self.reference_resolver = ReferenceResolver()
        
        # Initialize services
        self.question_service = QuestionService()
        self.search_service = SearchService()
        
        # Agent state per session
        self.session_states: Dict[str, QuestionStateMachine] = {}
        
        logger.info("Question Agent initialized")
    
    def can_handle(self, request: AgentRequest) -> bool:
        """Check if this agent can handle the request."""
        
        # Get intent from request metadata
        intent_data = request.metadata.get('intent', {})
        intent_type = intent_data.get('type', '')
        
        # Handle question-related intents
        question_intents = {
            IntentType.REQUEST_QUESTION.value,
            IntentType.ANSWER_QUESTION.value,
            IntentType.REQUEST_EXPLANATION.value,
            IntentType.REQUEST_HINT.value,
        }
        
        if intent_type in question_intents:
            return True
        
        # Check for question-related keywords in content
        content = request.content or request.message
        question_keywords = [
            'questão', 'questao', 'pergunta', 'exercício', 'exercicio',
            'resposta', 'alternativa', 'letra', 'opção', 'opcao',
            'explicação', 'explicacao', 'dica', 'hint',
            'enem', 'vestibular', 'prova'
        ]
        
        content_lower = content.lower()
        if any(keyword in content_lower for keyword in question_keywords):
            return True
        
        # Check current session state
        session_id = request.session_id
        if session_id and session_id in self.session_states:
            current_state = self.session_states[session_id].current_state
            # If we have an active question workflow, we can handle most requests
            if current_state != QuestionState.NO_QUESTION:
                return True
        
        return False
    
    async def process(self, request: AgentRequest) -> AgentResponse:
        """Process the request through the question workflow."""
        
        try:
            # Get or create session state machine
            session_id = request.session_id or "default"
            if session_id not in self.session_states:
                self.session_states[session_id] = QuestionStateMachine()
            
            state_machine = self.session_states[session_id]
            
            # Determine intent and route to appropriate handler
            intent_data = request.metadata.get('intent', {})
            intent_type = intent_data.get('type', '')
            entities = intent_data.get('entities', [])
            
            # Route based on intent
            if intent_type == IntentType.REQUEST_QUESTION.value:
                return await self._handle_question_request(request, state_machine, entities)
            
            elif intent_type == IntentType.ANSWER_QUESTION.value:
                return await self._handle_answer_submission(request, state_machine, entities)
            
            elif intent_type == IntentType.REQUEST_EXPLANATION.value:
                return await self._handle_explanation_request(request, state_machine)
            
            elif intent_type == IntentType.REQUEST_HINT.value:
                return await self._handle_hint_request(request, state_machine)
            
            else:
                # Try to infer action from current state and content
                return await self._handle_contextual_request(request, state_machine)
        
        except Exception as e:
            logger.error(f"Error processing question request: {e}")
            return AgentResponse(
                agent_name=self.name,
                content="Desculpe, ocorreu um erro ao processar sua solicitação sobre questões. Tente novamente.",
                confidence=0.0,
                metadata={'error': str(e)}
            )
    
    async def _handle_question_request(
        self, 
        request: AgentRequest, 
        state_machine: QuestionStateMachine,
        entities: List[Dict[str, Any]]
    ) -> AgentResponse:
        """Handle request for a new question."""
        
        try:
            # Extract search criteria from entities
            search_criteria = self._extract_search_criteria(entities)
            
            # Search for questions
            search_results = await self._search_questions(search_criteria)
            
            if not search_results:
                return AgentResponse(
                    agent_name=self.name,
                    content="Não encontrei questões que atendam aos seus critérios. Tente ser mais específico ou relaxar os filtros.",
                    confidence=0.3
                )
            
            # Get the best question
            question_id = search_results[0]['question_id']
            question_data = self.question_service.get_question_by_id(question_id)
            
            if not question_data:
                return AgentResponse(
                    agent_name=self.name,
                    content="Desculpe, não consegui carregar a questão encontrada. Tente novamente.",
                    confidence=0.0
                )
            
            # Update state machine
            success = state_machine.trigger_event(
                QuestionEvent.PRESENT_QUESTION,
                question_id=question_id,
                question_data=question_data
            )
            
            if not success:
                # Reset state machine and try again
                state_machine.reset()
                state_machine.trigger_event(
                    QuestionEvent.PRESENT_QUESTION,
                    question_id=question_id,
                    question_data=question_data
                )
            
            # Format question for display
            formatted_question = self.formatter.format_question(
                question_data,
                QuestionFormat.CHAT_MARKDOWN
            )
            
            # Get references
            references = self.reference_resolver.resolve_question_references(question_data)
            references_text = self.reference_resolver.format_references_for_display(references)
            
            # Build response content
            content_parts = [formatted_question.content]
            
            if references_text:
                content_parts.extend(["", references_text])
            
            return AgentResponse(
                agent_name=self.name,
                content='\n'.join(content_parts),
                confidence=0.9,
                metadata={
                    'question_id': question_id,
                    'current_state': state_machine.current_state.value,
                    'formatted_question': formatted_question.metadata,
                    'references_count': len(references),
                    'search_criteria': search_criteria
                }
            )
        
        except Exception as e:
            logger.error(f"Error handling question request: {e}")
            return AgentResponse(
                agent_name=self.name,
                content="Desculpe, ocorreu um erro ao buscar uma questão. Tente novamente.",
                confidence=0.0,
                metadata={'error': str(e)}
            )
    
    async def _handle_answer_submission(
        self, 
        request: AgentRequest, 
        state_machine: QuestionStateMachine,
        entities: List[Dict[str, Any]]
    ) -> AgentResponse:
        """Handle user's answer submission."""
        
        try:
            # Check if we have an active question
            if state_machine.current_state not in [QuestionState.QUESTION_PRESENTED, QuestionState.WAITING_ANSWER]:
                return AgentResponse(
                    agent_name=self.name,
                    content="Não há questão ativa para responder. Solicite uma nova questão primeiro.",
                    confidence=0.8
                )
            
            # Extract answer from entities or content
            user_answer = self._extract_answer(entities, request.content)
            
            if not user_answer:
                return AgentResponse(
                    agent_name=self.name,
                    content="Não consegui identificar sua resposta. Por favor, digite a letra da alternativa (A, B, C, D ou E).",
                    confidence=0.5
                )
            
            # Update state machine with answer
            success = state_machine.trigger_event(
                QuestionEvent.RECEIVE_ANSWER,
                user_answer=user_answer
            )
            
            if not success:
                return AgentResponse(
                    agent_name=self.name,
                    content="Erro ao processar sua resposta. Tente novamente.",
                    confidence=0.0
                )
            
            # Get question context
            context = state_machine.context
            question_data = context.question_data
            
            if not question_data:
                return AgentResponse(
                    agent_name=self.name,
                    content="Erro: dados da questão não encontrados. Solicite uma nova questão.",
                    confidence=0.0
                )
            
            # Check answer using question service
            answer_result = self.question_service.check_answer(
                question_id=context.question_id,
                user_answer=user_answer,
                user=None,  # Will be handled by the orchestrator
                session=None,  # Will be handled by the orchestrator
                time_spent=context.get_time_spent() or 0
            )
            
            if not answer_result:
                return AgentResponse(
                    agent_name=self.name,
                    content="Erro ao verificar sua resposta. Tente novamente.",
                    confidence=0.0
                )
            
            # Update context with result
            context.is_correct = answer_result.is_correct
            context.correct_answer = answer_result.correct_answer
            
            # Format feedback
            feedback = self.formatter.format_answer_feedback(
                user_answer=user_answer,
                correct_answer=answer_result.correct_answer,
                is_correct=answer_result.is_correct,
                explanation=answer_result.explanation,
                time_spent=context.get_time_spent()
            )
            
            # Trigger explanation event
            state_machine.trigger_event(QuestionEvent.SHOW_EXPLANATION)
            
            return AgentResponse(
                agent_name=self.name,
                content=feedback,
                confidence=1.0,
                metadata={
                    'question_id': context.question_id,
                    'user_answer': user_answer,
                    'correct_answer': answer_result.correct_answer,
                    'is_correct': answer_result.is_correct,
                    'time_spent': context.get_time_spent(),
                    'current_state': state_machine.current_state.value
                }
            )
        
        except Exception as e:
            logger.error(f"Error handling answer submission: {e}")
            return AgentResponse(
                agent_name=self.name,
                content="Desculpe, ocorreu um erro ao processar sua resposta. Tente novamente.",
                confidence=0.0,
                metadata={'error': str(e)}
            )
    
    async def _handle_explanation_request(
        self, 
        request: AgentRequest, 
        state_machine: QuestionStateMachine
    ) -> AgentResponse:
        """Handle request for explanation."""
        
        try:
            context = state_machine.context
            
            if not context.question_data:
                return AgentResponse(
                    agent_name=self.name,
                    content="Não há questão ativa para explicar. Responda a uma questão primeiro.",
                    confidence=0.8
                )
            
            # Get explanation from question data
            explanation = context.question_data.get('explanation', {})
            
            if not explanation:
                return AgentResponse(
                    agent_name=self.name,
                    content="Desculpe, não há explicação disponível para esta questão.",
                    confidence=0.5
                )
            
            # Format explanation
            explanation_text = self.formatter._format_explanation(explanation)
            
            if not explanation_text:
                return AgentResponse(
                    agent_name=self.name,
                    content="Desculpe, a explicação desta questão não está disponível no momento.",
                    confidence=0.5
                )
            
            # Update state
            state_machine.trigger_event(QuestionEvent.SHOW_EXPLANATION)
            
            content = f"📖 **Explicação:**\n\n{explanation_text}"
            
            return AgentResponse(
                agent_name=self.name,
                content=content,
                confidence=0.9,
                metadata={
                    'question_id': context.question_id,
                    'current_state': state_machine.current_state.value,
                    'explanation_shown': True
                }
            )
        
        except Exception as e:
            logger.error(f"Error handling explanation request: {e}")
            return AgentResponse(
                agent_name=self.name,
                content="Desculpe, ocorreu um erro ao buscar a explicação.",
                confidence=0.0,
                metadata={'error': str(e)}
            )
    
    async def _handle_hint_request(
        self, 
        request: AgentRequest, 
        state_machine: QuestionStateMachine
    ) -> AgentResponse:
        """Handle request for hint."""
        
        try:
            context = state_machine.context
            
            if not context.question_data:
                return AgentResponse(
                    agent_name=self.name,
                    content="Não há questão ativa para dar dicas. Solicite uma questão primeiro.",
                    confidence=0.8
                )
            
            if state_machine.current_state not in [QuestionState.QUESTION_PRESENTED, QuestionState.WAITING_ANSWER]:
                return AgentResponse(
                    agent_name=self.name,
                    content="Você já respondeu a questão. Solicite uma nova questão para receber dicas.",
                    confidence=0.8
                )
            
            # Update state and get hint
            state_machine.trigger_event(QuestionEvent.REQUEST_HINT)
            
            hint_number = context.hints_shown
            hint_text = self.formatter.format_hint(context.question_data, hint_number)
            
            if not hint_text:
                return AgentResponse(
                    agent_name=self.name,
                    content="Desculpe, não há mais dicas disponíveis para esta questão.",
                    confidence=0.5
                )
            
            return AgentResponse(
                agent_name=self.name,
                content=hint_text,
                confidence=0.8,
                metadata={
                    'question_id': context.question_id,
                    'hint_number': hint_number,
                    'total_hints_shown': context.hints_shown,
                    'current_state': state_machine.current_state.value
                }
            )
        
        except Exception as e:
            logger.error(f"Error handling hint request: {e}")
            return AgentResponse(
                agent_name=self.name,
                content="Desculpe, ocorreu um erro ao buscar uma dica.",
                confidence=0.0,
                metadata={'error': str(e)}
            )
    
    async def _handle_contextual_request(
        self, 
        request: AgentRequest, 
        state_machine: QuestionStateMachine
    ) -> AgentResponse:
        """Handle request based on current context and content."""
        
        content = (request.content or request.message).lower()
        
        # Check for answer patterns (A, B, C, D, E)
        import re
        answer_pattern = r'\b[abcde]\b'
        answer_match = re.search(answer_pattern, content)
        
        if answer_match and state_machine.current_state in [QuestionState.QUESTION_PRESENTED, QuestionState.WAITING_ANSWER]:
            # User is trying to answer
            entities = [{'entity_type': 'answer', 'value': answer_match.group().upper()}]
            return await self._handle_answer_submission(request, state_machine, entities)
        
        # Check for new question request
        if any(word in content for word in ['nova', 'outra', 'próxima', 'próximo', 'mais']):
            entities = []
            return await self._handle_question_request(request, state_machine, entities)
        
        # Default response based on current state
        current_state = state_machine.current_state
        
        if current_state == QuestionState.NO_QUESTION:
            return AgentResponse(
                agent_name=self.name,
                content="Olá! Posso ajudá-lo com questões de estudo. Digite 'quero uma questão' para começar ou especifique a matéria desejada.",
                confidence=0.7
            )
        
        elif current_state in [QuestionState.QUESTION_PRESENTED, QuestionState.WAITING_ANSWER]:
            return AgentResponse(
                agent_name=self.name,
                content="Há uma questão ativa aguardando sua resposta. Digite a letra da alternativa correta (A, B, C, D ou E) ou peça uma dica.",
                confidence=0.8
            )
        
        elif current_state == QuestionState.ANSWER_GIVEN:
            return AgentResponse(
                agent_name=self.name,
                content="Você já respondeu à questão. Posso mostrar a explicação ou você pode solicitar uma nova questão.",
                confidence=0.8
            )
        
        elif current_state == QuestionState.EXPLANATION_SHOWN:
            return AgentResponse(
                agent_name=self.name,
                content="Explicação já exibida. Deseja uma nova questão?",
                confidence=0.8
            )
        
        else:
            return AgentResponse(
                agent_name=self.name,
                content="Posso ajudá-lo com questões de estudo. O que você gostaria de fazer?",
                confidence=0.5
            )
    
    def _extract_search_criteria(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract search criteria from entities."""
        criteria = {}
        
        for entity in entities:
            entity_type = entity.get('entity_type', '').lower()
            value = entity.get('value', '')
            
            if entity_type == 'subject_area':
                criteria['subject_area'] = value
            elif entity_type == 'difficulty':
                criteria['difficulty'] = value
            elif entity_type == 'exam':
                criteria['exam'] = value
            elif entity_type == 'topic':
                criteria['specific_topic'] = value
        
        return criteria
    
    def _extract_answer(self, entities: List[Dict[str, Any]], content: str) -> Optional[str]:
        """Extract answer from entities or content."""
        
        # Check entities first
        for entity in entities:
            if entity.get('entity_type') == 'answer':
                return entity.get('value', '').upper()
        
        # Check content for answer patterns
        import re
        
        # Look for explicit answer patterns
        patterns = [
            r'\b(?:letra|alternativa|opção|resposta)\s+([A-Ea-e])\b',
            r'\b([A-Ea-e])\s*[\)\-\:]',
            r'^([A-Ea-e])$',
            r'\b([A-Ea-e])\b'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        return None
    
    async def _search_questions(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for questions using the search service."""
        try:
            # Use the search service to find questions
            results = self.search_service.search_questions(
                query=criteria.get('specific_topic', ''),
                subject_area=criteria.get('subject_area'),
                difficulty=criteria.get('difficulty'),
                exam=criteria.get('exam'),
                limit=10
            )
            
            return results
        
        except Exception as e:
            logger.error(f"Error searching questions: {e}")
            return []
    
    def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current state information for a session."""
        if session_id not in self.session_states:
            return None
        
        state_machine = self.session_states[session_id]
        return state_machine.get_state_info()
    
    def reset_session(self, session_id: str) -> bool:
        """Reset session state."""
        if session_id in self.session_states:
            self.session_states[session_id].reset()
            return True
        return False
    
    def get_agent_statistics(self) -> Dict[str, Any]:
        """Get agent statistics."""
        total_sessions = len(self.session_states)
        active_questions = sum(
            1 for sm in self.session_states.values() 
            if sm.current_state != QuestionState.NO_QUESTION
        )
        
        # State distribution
        state_counts = {}
        for sm in self.session_states.values():
            state = sm.current_state.value
            state_counts[state] = state_counts.get(state, 0) + 1
        
        return {
            'total_sessions': total_sessions,
            'active_questions': active_questions,
            'state_distribution': state_counts,
            'capabilities': [cap.value for cap in self.capabilities],
            'priority': self.priority
        }