"""
Sistema de Agentes do Marriplan - Fase 4

Este módulo implementa a arquitetura completa de agentes para processar
diferentes tipos de interações no sistema educacional, incluindo
orquestração, roteamento, registro, comunicação, questões, chat e RAG.
"""

from .base import (
    BaseAgent,
    AgentResponse,
    AgentCapability,
    AgentPriority,
    AgentRegistry as BaseAgentRegistry
)
from .orchestrator import OrchestratorAgent, PipelineStage, PipelineContext
from .routing import (
    BaseRouter, SimpleRouter, WeightedRouter, CascadingRouter,
    SmartRouter, RoutingStrategy, RouterFactory
)
from .registry import AgentRegistry, AgentStatus, AgentRegistration, get_global_registry
from .pipeline import (
    PipelineProcessor, TaskQueue, WorkerPool, PipelineTask,
    TaskStatus, TaskPriority, get_global_processor
)
from .communication import (
    CommunicationBus, AgentMessage, MessageType, MessagePriority,
    CollaborationManager, DelegationManager, get_global_communication_bus
)
from .question import (
    QuestionAgent, QuestionStateMachine, QuestionState, QuestionEvent,
    QuestionFormatter, QuestionFormat, ReferenceResolver, ReferenceType
)
from .chat_agent import ChatAgent
from .rag_agent import RAGAgent

__all__ = [
    # Base classes (Fase 1)
    'BaseAgent',
    'AgentResponse',
    'AgentCapability',
    'AgentPriority',
    'BaseAgentRegistry',

    # Orchestrator (Fase 2)
    'OrchestratorAgent',
    'PipelineStage',
    'PipelineContext',

    # Routing (Fase 2)
    'BaseRouter',
    'SimpleRouter',
    'WeightedRouter',
    'CascadingRouter',
    'SmartRouter',
    'RoutingStrategy',
    'RouterFactory',

    # Registry (Fase 2)
    'AgentRegistry',
    'AgentStatus',
    'AgentRegistration',
    'get_global_registry',

    # Pipeline (Fase 2)
    'PipelineProcessor',
    'TaskQueue',
    'WorkerPool',
    'PipelineTask',
    'TaskStatus',
    'TaskPriority',
    'get_global_processor',

    # Communication (Fase 2)
    'CommunicationBus',
    'AgentMessage',
    'MessageType',
    'MessagePriority',
    'CollaborationManager',
    'DelegationManager',
    'get_global_communication_bus',

    # Question Agent (Fase 3)
    'QuestionAgent',
    'QuestionStateMachine',
    'QuestionState',
    'QuestionEvent',
    'QuestionFormatter',
    'QuestionFormat',
    'ReferenceResolver',
    'ReferenceType',

    # Chat & RAG Agents (Fase 4)
    'ChatAgent',
    'RAGAgent',
]