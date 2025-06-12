"""
Intelligent routing system for selecting appropriate agents.
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging
from enum import Enum

from app.core.agents.base import BaseAgent, AgentCapability
from app.core.models.agent_models import AgentRequest
from app.core.services.intent_detection import IntentType


logger = logging.getLogger(__name__)


class RoutingStrategy(Enum):
    """Available routing strategies."""
    SIMPLE = "simple"
    WEIGHTED = "weighted"
    ML_BASED = "ml_based"
    CASCADING = "cascading"


@dataclass
class RoutingCriteria:
    """Criteria for agent routing decisions."""
    intent_type: IntentType
    confidence_threshold: float = 0.5
    max_agents: int = 3
    prefer_specialists: bool = True
    allow_fallback: bool = True
    timeout_seconds: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentScore:
    """Score assigned to an agent for routing."""
    agent: BaseAgent
    score: float
    reasoning: str
    capability_match: float
    priority_bonus: float
    context_bonus: float


class BaseRouter(ABC):
    """Abstract base class for routing strategies."""
    
    @abstractmethod
    async def route(self, 
                   intent: Any, 
                   request: AgentRequest, 
                   agent_registry: Any) -> List[BaseAgent]:
        """Route request to appropriate agents."""
        pass


class SimpleRouter(BaseRouter):
    """Simple routing based on intent-capability mapping."""
    
    def __init__(self):
        self.intent_capability_map = {
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
    
    async def route(self, 
                   intent: Any, 
                   request: AgentRequest, 
                   agent_registry: Any) -> List[BaseAgent]:
        """Simple routing based on intent type."""
        if not agent_registry:
            return []
        
        # Get required capabilities
        intent_type = getattr(intent, 'intent_type', None) or getattr(intent, 'type', None)
        required_capabilities = self.intent_capability_map.get(
            intent_type,
            [AgentCapability.GENERAL_CHAT]
        )
        
        # Find agents with required capabilities
        selected_agents = []
        for capability in required_capabilities:
            agents = agent_registry.get_agents_by_capability(capability)
            selected_agents.extend(agents)
        
        # Remove duplicates and sort by priority
        unique_agents = {}
        for agent in selected_agents:
            if agent.name not in unique_agents:
                unique_agents[agent.name] = agent
        
        agents = list(unique_agents.values())
        agents.sort(key=lambda a: a.priority, reverse=True)
        
        # Limit to max 3 agents
        return agents[:3]


class WeightedRouter(BaseRouter):
    """Weighted routing with scoring system."""
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or {
            'capability_match': 0.4,
            'priority': 0.2,
            'context_match': 0.2,
            'confidence': 0.1,
            'performance': 0.1
        }
        
        # Intent scoring multipliers
        self.intent_multipliers = {
            IntentType.REQUEST_QUESTION: 1.0,
            IntentType.ANSWER_QUESTION: 1.0,
            IntentType.REQUEST_EXPLANATION: 0.9,
            IntentType.REQUEST_HINT: 0.8,
            IntentType.GREETING: 0.5,
            IntentType.FAREWELL: 0.5,
            IntentType.HELP: 0.7,
            IntentType.FEEDBACK: 0.6,
            IntentType.SEARCH_CONTENT: 1.0,
            IntentType.STUDY_PLAN: 0.9,
            IntentType.PROGRESS_CHECK: 0.7,
            IntentType.GENERAL_CHAT: 0.6,
            IntentType.UNKNOWN: 0.3
        }
    
    async def route(self, 
                   intent: Any, 
                   request: AgentRequest, 
                   agent_registry: Any) -> List[BaseAgent]:
        """Weighted routing with comprehensive scoring."""
        if not agent_registry:
            return []
        
        # Get all active agents
        all_agents = agent_registry.get_all_active_agents()
        
        # Score each agent
        agent_scores = []
        for agent in all_agents:
            score = await self._score_agent(agent, intent, request, agent_registry)
            agent_scores.append(score)
        
        # Sort by score
        agent_scores.sort(key=lambda s: s.score, reverse=True)
        
        # Apply confidence threshold
        intent_type = getattr(intent, 'intent_type', None) or getattr(intent, 'type', None)
        min_score = self.intent_multipliers.get(intent_type, 0.5) * 0.5
        filtered_scores = [s for s in agent_scores if s.score >= min_score]
        
        # Limit results
        selected_scores = filtered_scores[:3]
        
        logger.info(f"Routing scores for intent {intent_type.value if intent_type else 'unknown'}:")
        for score in selected_scores:
            logger.info(f"  {score.agent.name}: {score.score:.3f} - {score.reasoning}")
        
        return [s.agent for s in selected_scores]
    
    async def _score_agent(self, 
                          agent: BaseAgent, 
                          intent: Any, 
                          request: AgentRequest,
                          agent_registry: Any) -> AgentScore:
        """Score an individual agent for routing."""
        
        # 1. Capability match score
        capability_score = self._calculate_capability_score(agent, intent)
        
        # 2. Priority bonus (normalized)
        priority_score = min(agent.priority / 100.0, 1.0)
        
        # 3. Context bonus
        context_score = self._calculate_context_score(agent, intent, request)
        
        # 4. Performance score (from metrics if available)
        performance_score = self._calculate_performance_score(agent, agent_registry)
        
        # 5. Confidence multiplier
        confidence_multiplier = min(intent.confidence * 2, 1.0)
        
        # Calculate weighted score
        total_score = (
            self.weights['capability_match'] * capability_score +
            self.weights['priority'] * priority_score +
            self.weights['context_match'] * context_score +
            self.weights['performance'] * performance_score
        ) * confidence_multiplier
        
        # Apply intent multiplier
        intent_type = getattr(intent, 'intent_type', None) or getattr(intent, 'type', None)
        intent_multiplier = self.intent_multipliers.get(intent_type, 0.5)
        final_score = total_score * intent_multiplier
        
        reasoning = (f"Cap:{capability_score:.2f} Pri:{priority_score:.2f} "
                    f"Ctx:{context_score:.2f} Perf:{performance_score:.2f} "
                    f"Conf:{confidence_multiplier:.2f} Intent:{intent_multiplier:.2f}")
        
        return AgentScore(
            agent=agent,
            score=final_score,
            reasoning=reasoning,
            capability_match=capability_score,
            priority_bonus=priority_score,
            context_bonus=context_score
        )
    
    def _calculate_capability_score(self, agent: BaseAgent, intent: Any) -> float:
        """Calculate how well agent capabilities match intent."""
        # Map intent to required capabilities
        required_caps = {
            IntentType.REQUEST_QUESTION: {AgentCapability.QUESTION_MANAGEMENT: 1.0},
            IntentType.ANSWER_QUESTION: {AgentCapability.QUESTION_MANAGEMENT: 1.0},
            IntentType.REQUEST_EXPLANATION: {
                AgentCapability.EXPLANATION: 1.0,
                AgentCapability.QUESTION_MANAGEMENT: 0.7
            },
            IntentType.REQUEST_HINT: {AgentCapability.QUESTION_MANAGEMENT: 0.8},
            IntentType.GREETING: {AgentCapability.GENERAL_CHAT: 0.5},
            IntentType.FAREWELL: {AgentCapability.GENERAL_CHAT: 0.5},
            IntentType.HELP: {AgentCapability.GENERAL_CHAT: 0.7},
            IntentType.FEEDBACK: {AgentCapability.GENERAL_CHAT: 0.6},
            IntentType.SEARCH_CONTENT: {AgentCapability.RAG_SEARCH: 1.0},
            IntentType.STUDY_PLAN: {AgentCapability.STUDY_PLANNING: 1.0},
            IntentType.PROGRESS_CHECK: {AgentCapability.GENERAL_CHAT: 0.7},
            IntentType.GENERAL_CHAT: {AgentCapability.GENERAL_CHAT: 0.8},
            IntentType.UNKNOWN: {AgentCapability.GENERAL_CHAT: 0.3}
        }
        
        intent_type = getattr(intent, 'intent_type', None) or getattr(intent, 'type', None)
        intent_requirements = required_caps.get(intent_type, {})
        
        # Calculate match score
        total_score = 0.0
        max_possible = sum(intent_requirements.values())
        
        for capability, weight in intent_requirements.items():
            if capability in agent.capabilities:
                total_score += weight
        
        return total_score / max_possible if max_possible > 0 else 0.0
    
    def _calculate_context_score(self, agent: BaseAgent, intent: Any, request: AgentRequest) -> float:
        """Calculate context-based bonus score."""
        score = 0.0
        
        # Check for subject/topic entities
        entities = getattr(intent, 'entities', [])
        if entities:
            # Agent specialization bonus
            agent_name_lower = agent.name.lower()
            for entity in entities:
                entity_value = entity.value.lower()
                
                # Subject specialization
                if 'matemática' in entity_value and 'math' in agent_name_lower:
                    score += 0.3
                elif 'português' in entity_value and 'language' in agent_name_lower:
                    score += 0.3
                elif 'questão' in entity_value and 'question' in agent_name_lower:
                    score += 0.2
        
        # Session context bonus
        if request.metadata:
            # Active question context
            if request.metadata.get('has_active_question'):
                if AgentCapability.QUESTION_MANAGEMENT in agent.capabilities:
                    score += 0.2
            
            # Previous interaction success
            if request.metadata.get('previous_successful_agent') == agent.name:
                score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_performance_score(self, agent: BaseAgent, agent_registry: Any) -> float:
        """Calculate performance-based score from agent metrics."""
        try:
            if hasattr(agent, 'get_metrics'):
                metrics = agent.get_metrics()
                
                # Success rate component
                success_rate = metrics.get('success_rate', 0.5)
                
                # Response time component (faster is better, normalize to 0-1)
                avg_time = metrics.get('average_response_time', 5.0)
                time_score = max(0.0, 1.0 - (avg_time / 10.0))  # 10 seconds = 0 score
                
                # Total requests component (more experience is better)
                total_requests = metrics.get('total_requests', 0)
                experience_score = min(total_requests / 100.0, 1.0)  # 100 requests = max
                
                # Weighted performance score
                performance_score = (
                    0.5 * success_rate +
                    0.3 * time_score +
                    0.2 * experience_score
                )
                
                return performance_score
                
        except Exception as e:
            logger.warning(f"Could not get metrics for agent {agent.name}: {e}")
        
        # Default performance score
        return 0.5


class CascadingRouter(BaseRouter):
    """Cascading router that tries multiple strategies."""
    
    def __init__(self):
        self.routers = [
            WeightedRouter(),
            SimpleRouter()
        ]
    
    async def route(self, 
                   intent: Any, 
                   request: AgentRequest, 
                   agent_registry: Any) -> List[BaseAgent]:
        """Try routers in sequence until we get results."""
        
        for router in self.routers:
            try:
                agents = await router.route(intent, request, agent_registry)
                if agents:
                    logger.info(f"Cascading router succeeded with {type(router).__name__}")
                    return agents
            except Exception as e:
                logger.warning(f"Router {type(router).__name__} failed: {e}")
                continue
        
        # Ultimate fallback
        logger.warning("All routers failed, using fallback")
        if agent_registry:
            fallback_agents = agent_registry.get_agents_by_capability(
                AgentCapability.GENERAL_CHAT
            )
            return fallback_agents[:1]  # Just one fallback agent
        
        return []


class RouterFactory:
    """Factory for creating router instances."""
    
    @staticmethod
    def create_router(strategy: RoutingStrategy = RoutingStrategy.WEIGHTED, 
                     **kwargs) -> BaseRouter:
        """Create router instance based on strategy."""
        
        if strategy == RoutingStrategy.SIMPLE:
            return SimpleRouter()
        
        elif strategy == RoutingStrategy.WEIGHTED:
            weights = kwargs.get('weights')
            return WeightedRouter(weights=weights)
        
        elif strategy == RoutingStrategy.CASCADING:
            return CascadingRouter()
        
        elif strategy == RoutingStrategy.ML_BASED:
            # Placeholder for future ML-based routing
            logger.warning("ML-based routing not implemented, falling back to weighted")
            return WeightedRouter()
        
        else:
            raise ValueError(f"Unknown routing strategy: {strategy}")


class SmartRouter:
    """Main router class with adaptive strategy selection."""
    
    def __init__(self, 
                 default_strategy: RoutingStrategy = RoutingStrategy.WEIGHTED,
                 enable_adaptation: bool = True):
        """Initialize smart router."""
        self.default_strategy = default_strategy
        self.enable_adaptation = enable_adaptation
        self.router_factory = RouterFactory()
        
        # Performance tracking for adaptation
        self.strategy_performance: Dict[str, Dict[str, float]] = {}
        
        # Current router instance
        self.current_router = self.router_factory.create_router(default_strategy)
    
    async def route(self, 
                   intent: Any, 
                   request: AgentRequest, 
                   agent_registry: Any) -> List[BaseAgent]:
        """Route with adaptive strategy selection."""
        
        # Choose strategy based on context and performance
        strategy = self._choose_strategy(intent, request)
        
        # Create router if needed
        if not isinstance(self.current_router, self._get_router_class(strategy)):
            self.current_router = self.router_factory.create_router(strategy)
        
        # Route the request
        try:
            agents = await self.current_router.route(intent, request, agent_registry)
            
            # Track success
            self._track_performance(strategy, success=True, response_time=0.0)
            
            return agents
            
        except Exception as e:
            logger.error(f"Routing failed with strategy {strategy}: {e}")
            
            # Track failure
            self._track_performance(strategy, success=False, response_time=0.0)
            
            # Fallback to cascading router
            if strategy != RoutingStrategy.CASCADING:
                fallback_router = self.router_factory.create_router(RoutingStrategy.CASCADING)
                return await fallback_router.route(intent, request, agent_registry)
            
            raise
    
    def _choose_strategy(self, intent: Any, request: AgentRequest) -> RoutingStrategy:
        """Choose optimal routing strategy based on context."""
        
        # For now, use simple heuristics
        # In future, implement ML-based strategy selection
        
        # High confidence intents -> simple routing
        if intent.confidence > 0.9:
            return RoutingStrategy.SIMPLE
        
        # Complex intents -> weighted routing
        intent_type = getattr(intent, 'intent_type', None) or getattr(intent, 'type', None)
        if intent_type in [IntentType.REQUEST_EXPLANATION, IntentType.SEARCH_CONTENT]:
            return RoutingStrategy.WEIGHTED
        
        # Unknown or low confidence -> cascading
        if intent_type == IntentType.UNKNOWN or intent.confidence < 0.5:
            return RoutingStrategy.CASCADING
        
        # Default
        return self.default_strategy
    
    def _get_router_class(self, strategy: RoutingStrategy) -> type:
        """Get router class for strategy."""
        strategy_classes = {
            RoutingStrategy.SIMPLE: SimpleRouter,
            RoutingStrategy.WEIGHTED: WeightedRouter,
            RoutingStrategy.CASCADING: CascadingRouter
        }
        return strategy_classes.get(strategy, WeightedRouter)
    
    def _track_performance(self, strategy: RoutingStrategy, success: bool, response_time: float):
        """Track performance metrics for strategy adaptation."""
        if not self.enable_adaptation:
            return
        
        strategy_name = strategy.value
        if strategy_name not in self.strategy_performance:
            self.strategy_performance[strategy_name] = {
                'total_requests': 0,
                'successful_requests': 0,
                'total_response_time': 0.0
            }
        
        metrics = self.strategy_performance[strategy_name]
        metrics['total_requests'] += 1
        if success:
            metrics['successful_requests'] += 1
        metrics['total_response_time'] += response_time
    
    def get_performance_report(self) -> Dict[str, Dict[str, float]]:
        """Get performance report for all strategies."""
        report = {}
        for strategy, metrics in self.strategy_performance.items():
            total = metrics['total_requests']
            if total > 0:
                report[strategy] = {
                    'success_rate': metrics['successful_requests'] / total,
                    'average_response_time': metrics['total_response_time'] / total,
                    'total_requests': total
                }
        return report