"""
Orchestrator Agent implementation for coordinating other agents.
"""
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import asyncio
import logging
from datetime import datetime
from enum import Enum

from app.core.agents.base import BaseAgent, AgentResponse, AgentCapability
from app.core.models.agent_models import (
    AgentRequest,
    AgentTask,
    AgentCommunication,
    AgentMetrics
)
from app.core.services.intent_detection import IntentDetector, IntentType
from app.core.context import ContextManager


logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """Pipeline stages for processing."""
    INTENT_ANALYSIS = "intent_analysis"
    AGENT_SELECTION = "agent_selection"
    PRE_PROCESSING = "pre_processing"
    AGENT_EXECUTION = "agent_execution"
    POST_PROCESSING = "post_processing"
    RESPONSE_COMPOSITION = "response_composition"


@dataclass
class PipelineContext:
    """Context for pipeline execution."""
    request: AgentRequest
    intent: Optional[Any] = None
    selected_agents: List[BaseAgent] = field(default_factory=list)
    agent_responses: List[AgentResponse] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    stage: PipelineStage = PipelineStage.INTENT_ANALYSIS
    start_time: datetime = field(default_factory=datetime.now)
    
    def add_response(self, response: AgentResponse):
        """Add agent response to context."""
        self.agent_responses.append(response)
    
    def get_execution_time(self) -> float:
        """Get total execution time in seconds."""
        return (datetime.now() - self.start_time).total_seconds()


class OrchestratorAgent(BaseAgent):
    """
    Main orchestrator agent that coordinates all other agents.
    """
    
    def __init__(self, 
                 agent_registry: Optional[Any] = None,
                 router: Optional[Any] = None,
                 intent_detector: Optional[IntentDetector] = None,
                 context_manager: Optional[ContextManager] = None):
        """Initialize orchestrator with dependencies."""
        super().__init__(
            name="OrchestratorAgent",
            capabilities=[AgentCapability.GENERAL_CHAT],
            priority=100  # Highest priority
        )
        
        self.agent_registry = agent_registry
        self.router = router
        self.intent_detector = intent_detector or IntentDetector()
        self.context_manager = context_manager or ContextManager()
        
        # Pipeline configuration
        self.pipeline_stages = [
            self._analyze_intent,
            self._select_agents,
            self._pre_process,
            self._execute_agents,
            self._post_process,
            self._compose_response
        ]
        
        # Metrics tracking
        self.metrics = AgentMetrics(
            agent_name=self.name,
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            average_response_time_ms=0.0
        )
    
    def can_handle(self, request: AgentRequest) -> bool:
        """Orchestrator can handle all requests."""
        return True
    
    async def process(self, request: AgentRequest) -> AgentResponse:
        """
        Process request through the agent pipeline.
        """
        context = PipelineContext(request=request)
        
        try:
            # Update metrics
            self.metrics.total_requests += 1
            
            # Execute pipeline stages
            for stage_func in self.pipeline_stages:
                context = await stage_func(context)
                
                # Check for early exit
                if context.metadata.get('early_exit', False):
                    break
            
            # Create final response
            response = self._create_final_response(context)
            
            # Update success metrics
            self.metrics.successful_requests += 1
            self._update_average_response_time(context.get_execution_time() * 1000)  # Convert to ms
            
            return response
            
        except Exception as e:
            logger.error(f"Orchestrator error: {str(e)}", exc_info=True)
            self.metrics.failed_requests += 1
            
            return AgentResponse(
                content=f"Desculpe, ocorreu um erro ao processar sua solicitação: {str(e)}",
                confidence=0.0,
                agent_name=self.name,
                metadata={'error': str(e), 'stage': context.stage.value}
            )
    
    async def _analyze_intent(self, context: PipelineContext) -> PipelineContext:
        """Analyze user intent."""
        context.stage = PipelineStage.INTENT_ANALYSIS
        
        # Get session context
        session_context = self.context_manager.get_or_create_context(
            session_id=context.request.session_id,
            user_id=context.request.user_id or "anonymous"
        )
        
        # Detect intent
        context.intent = self.intent_detector.detect(
            context.request.content,
            context=session_context.to_dict() if session_context else {}
        )
        
        intent_type = getattr(context.intent, 'intent_type', None) or getattr(context.intent, 'type', None)
        
        logger.info(f"Detected intent: {intent_type.value if intent_type else 'unknown'} "
                   f"with confidence {context.intent.confidence}")
        
        context.metadata['intent'] = {
            'type': intent_type.value if intent_type else 'unknown',
            'confidence': context.intent.confidence,
            'entities': [{'type': e.entity_type, 'value': e.value} 
                        for e in context.intent.entities]
        }
        
        return context
    
    async def _select_agents(self, context: PipelineContext) -> PipelineContext:
        """Select appropriate agents based on intent and context."""
        context.stage = PipelineStage.AGENT_SELECTION
        
        if self.router:
            # Use router for intelligent selection
            selected_agents = await self.router.route(
                context.intent,
                context.request,
                self.agent_registry
            )
        else:
            # Fallback: select based on capabilities
            selected_agents = self._select_by_capability(context.intent)
        
        context.selected_agents = selected_agents
        context.metadata['selected_agents'] = [agent.name for agent in selected_agents]
        
        logger.info(f"Selected {len(selected_agents)} agents: "
                   f"{', '.join(agent.name for agent in selected_agents)}")
        
        return context
    
    async def _pre_process(self, context: PipelineContext) -> PipelineContext:
        """Pre-process request before agent execution."""
        context.stage = PipelineStage.PRE_PROCESSING
        
        # Update conversation memory
        if self.context_manager:
            self.context_manager.add_message_to_memory(
                context.request.session_id,
                role='user',
                content=context.request.content,
                intent=getattr(context.intent, 'type', {}).value if hasattr(getattr(context.intent, 'type', {}), 'value') else None
            )
        
        # Check for special cases
        intent_type = getattr(context.intent, 'intent_type', None) or getattr(context.intent, 'type', None)
        if intent_type == IntentType.GREETING:
            # Handle greetings quickly
            context.metadata['early_exit'] = True
            context.add_response(AgentResponse(
                content="Olá! Como posso ajudá-lo hoje?",
                confidence=1.0,
                agent_name=self.name
            ))
        
        return context
    
    async def _execute_agents(self, context: PipelineContext) -> PipelineContext:
        """Execute selected agents."""
        context.stage = PipelineStage.AGENT_EXECUTION
        
        # Skip if early exit
        if context.metadata.get('early_exit', False):
            return context
        
        # Execute agents based on strategy
        execution_strategy = context.metadata.get('execution_strategy', 'sequential')
        
        if execution_strategy == 'parallel':
            responses = await self._execute_parallel(context)
        else:
            responses = await self._execute_sequential(context)
        
        context.agent_responses.extend(responses)
        
        return context
    
    async def _execute_sequential(self, context: PipelineContext) -> List[AgentResponse]:
        """Execute agents sequentially."""
        responses = []
        
        for agent in context.selected_agents:
            try:
                # Create agent-specific request
                agent_request = AgentRequest(
                    message=context.request.message,
                    content=context.request.content,
                    session_id=context.request.session_id,
                    user_id=context.request.user_id,
                    metadata={
                        **context.request.metadata,
                        'intent': context.metadata['intent'],
                        'previous_responses': [r.dict() for r in responses]
                    }
                )
                
                # Execute agent
                response = await agent.process(agent_request)
                responses.append(response)
                
                # Check if we should continue
                if response.metadata.get('final_response', False):
                    break
                    
            except Exception as e:
                logger.error(f"Error executing agent {agent.name}: {str(e)}")
                responses.append(AgentResponse(
                    content=f"Erro ao executar {agent.name}",
                    confidence=0.0,
                    agent_name=agent.name,
                    metadata={'error': str(e)}
                ))
        
        return responses
    
    async def _execute_parallel(self, context: PipelineContext) -> List[AgentResponse]:
        """Execute agents in parallel."""
        tasks = []
        
        for agent in context.selected_agents:
            # Create agent-specific request
            agent_request = AgentRequest(
                message=context.request.message,
                content=context.request.content,
                session_id=context.request.session_id,
                user_id=context.request.user_id,
                metadata={
                    **context.request.metadata,
                    'intent': context.metadata['intent']
                }
            )
            
            # Create task
            task = asyncio.create_task(agent.process(agent_request))
            tasks.append((agent.name, task))
        
        # Wait for all tasks
        responses = []
        for agent_name, task in tasks:
            try:
                response = await task
                responses.append(response)
            except Exception as e:
                logger.error(f"Error executing agent {agent_name}: {str(e)}")
                responses.append(AgentResponse(
                    content=f"Erro ao executar {agent_name}",
                    confidence=0.0,
                    agent_name=agent_name,
                    metadata={'error': str(e)}
                ))
        
        return responses
    
    async def _post_process(self, context: PipelineContext) -> PipelineContext:
        """Post-process agent responses."""
        context.stage = PipelineStage.POST_PROCESSING
        
        # Skip if early exit
        if context.metadata.get('early_exit', False):
            return context
        
        # Analyze responses
        if context.agent_responses:
            # Sort by confidence
            context.agent_responses.sort(key=lambda r: r.confidence, reverse=True)
            
            # Check for conflicts
            self._check_response_conflicts(context)
            
            # Merge metadata
            merged_metadata = {}
            for response in context.agent_responses:
                merged_metadata.update(response.metadata)
            context.metadata['merged_response_metadata'] = merged_metadata
        
        return context
    
    async def _compose_response(self, context: PipelineContext) -> PipelineContext:
        """Compose final response from agent outputs."""
        context.stage = PipelineStage.RESPONSE_COMPOSITION
        
        # Already have response for early exit
        if context.metadata.get('early_exit', False):
            return context
        
        if not context.agent_responses:
            # No agents responded
            context.add_response(AgentResponse(
                content="Desculpe, não consegui processar sua solicitação.",
                confidence=0.0,
                agent_name=self.name
            ))
        elif len(context.agent_responses) == 1:
            # Single response, use as is
            pass
        else:
            # Multiple responses, need to combine
            combined_response = self._combine_responses(context.agent_responses)
            context.agent_responses = [combined_response]
        
        return context
    
    def _create_final_response(self, context: PipelineContext) -> AgentResponse:
        """Create final response from pipeline context."""
        if context.agent_responses:
            final_response = context.agent_responses[0]
            
            # Enhance metadata
            final_response.metadata.update({
                'pipeline_execution_time': context.get_execution_time(),
                'pipeline_stages_completed': context.stage.value,
                'agents_consulted': context.metadata.get('selected_agents', [])
            })
            
            return final_response
        
        # Fallback response
        return AgentResponse(
            content="Não foi possível processar sua solicitação.",
            confidence=0.0,
            agent_name=self.name,
            metadata={
                'pipeline_execution_time': context.get_execution_time(),
                'error': 'No response generated'
            }
        )
    
    def _select_by_capability(self, intent: Any) -> List[BaseAgent]:
        """Select agents based on intent and capabilities."""
        if not self.agent_registry:
            return []
        
        # Map intent to capabilities
        capability_map = {
            IntentType.REQUEST_QUESTION: [AgentCapability.QUESTION_MANAGEMENT],
            IntentType.ANSWER_QUESTION: [AgentCapability.QUESTION_MANAGEMENT],
            IntentType.REQUEST_EXPLANATION: [AgentCapability.EXPLANATION],
            IntentType.REQUEST_HINT: [AgentCapability.QUESTION_MANAGEMENT],
            IntentType.GREETING: [AgentCapability.GENERAL_CHAT],
            IntentType.FAREWELL: [AgentCapability.GENERAL_CHAT],
            IntentType.HELP: [AgentCapability.GENERAL_CHAT],
            IntentType.FEEDBACK: [AgentCapability.GENERAL_CHAT],
            IntentType.SEARCH_CONTENT: [AgentCapability.RAG_SEARCH],
            IntentType.STUDY_PLAN: [AgentCapability.STUDY_PLANNING],
            IntentType.PROGRESS_CHECK: [AgentCapability.GENERAL_CHAT],
            IntentType.GENERAL_CHAT: [AgentCapability.GENERAL_CHAT],
            IntentType.UNKNOWN: [AgentCapability.GENERAL_CHAT]
        }
        
        intent_type = getattr(intent, 'intent_type', None) or getattr(intent, 'type', None)
        required_capabilities = capability_map.get(
            intent_type, 
            [AgentCapability.GENERAL_CHAT]
        )
        
        # Get agents with required capabilities
        selected_agents = []
        for capability in required_capabilities:
            agents = self.agent_registry.get_agents_by_capability(capability)
            selected_agents.extend(agents)
        
        # Remove duplicates and sort by priority
        seen = set()
        unique_agents = []
        for agent in selected_agents:
            if agent.name not in seen:
                seen.add(agent.name)
                unique_agents.append(agent)
        
        return sorted(unique_agents, key=lambda a: a.priority, reverse=True)
    
    def _check_response_conflicts(self, context: PipelineContext):
        """Check for conflicts in agent responses."""
        if len(context.agent_responses) < 2:
            return
        
        # Check confidence spread
        confidences = [r.confidence for r in context.agent_responses]
        confidence_spread = max(confidences) - min(confidences)
        
        if confidence_spread > 0.5:
            logger.warning(f"High confidence spread detected: {confidence_spread}")
            context.metadata['confidence_conflict'] = True
    
    def _combine_responses(self, responses: List[AgentResponse]) -> AgentResponse:
        """Combine multiple agent responses into one."""
        # For now, use the highest confidence response
        # In future, implement more sophisticated merging
        best_response = max(responses, key=lambda r: r.confidence)
        
        # Add information about other responses
        best_response.metadata['alternative_responses'] = [
            {
                'agent': r.agent_name,
                'confidence': r.confidence,
                'summary': r.content[:100] + '...' if len(r.content) > 100 else r.content
            }
            for r in responses if r != best_response
        ]
        
        return best_response
    
    def _update_average_response_time(self, response_time_ms: float):
        """Update average response time metric."""
        total = self.metrics.successful_requests
        if total > 0:
            # Calculate new average
            current_avg = self.metrics.average_response_time_ms
            self.metrics.average_response_time_ms = (
                (current_avg * (total - 1) + response_time_ms) / total
            )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get orchestrator metrics."""
        return {
            'agent_name': self.metrics.agent_name,
            'total_requests': self.metrics.total_requests,
            'successful_requests': self.metrics.successful_requests,
            'failed_requests': self.metrics.failed_requests,
            'average_response_time': self.metrics.average_response_time_ms / 1000.0,  # Convert back to seconds
            'success_rate': (
                self.metrics.successful_requests / self.metrics.total_requests
                if self.metrics.total_requests > 0 else 0.0
            )
        }