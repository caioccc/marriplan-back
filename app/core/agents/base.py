"""
Classes base e interfaces para o sistema de agentes
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
import logging

logger = logging.getLogger(__name__)


class AgentCapability(Enum):
    """Capacidades que um agente pode ter"""
    QUESTION_HANDLING = "question_handling"
    QUESTION_MANAGEMENT = "question_management"  # Fase 2 compatibility
    ANSWER_VERIFICATION = "answer_verification"
    CHAT_CONVERSATION = "chat_conversation"
    GENERAL_CHAT = "general_chat"  # Adicionado para compatibilidade
    STUDY_RECOMMENDATION = "study_recommendation"
    STUDY_PLANNING = "study_planning"  # Fase 2 compatibility
    EXPLANATION_GENERATION = "explanation_generation"
    EXPLANATION = "explanation"  # Fase 2 compatibility
    REFERENCE_RETRIEVAL = "reference_retrieval"
    PROGRESS_TRACKING = "progress_tracking"
    RAG_SEARCH = "rag_search"


class AgentPriority(Enum):
    """Prioridade de execução do agente"""
    CRITICAL = 1  # Sempre executado primeiro
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5  # Executado por último


@dataclass
class AgentResponse:
    """Resposta padronizada de um agente"""
    agent_name: str
    success: bool = True  # Fase 2 compatibility
    confidence: float = 1.0  # 0.0 a 1.0
    message: Optional[str] = None
    content: Optional[str] = None  # Fase 2 compatibility - alias for message
    data: Dict[str, Any] = field(default_factory=dict)
    context_updates: Dict[str, Any] = field(default_factory=dict)
    next_agent: Optional[str] = None  # Sugestão de próximo agente
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Post-init to handle content/message compatibility."""
        if self.content is None and self.message is not None:
            self.content = self.message
        elif self.message is None and self.content is not None:
            self.message = self.content
    
    def should_continue(self) -> bool:
        """Indica se o processamento deve continuar com outros agentes"""
        return self.success and self.confidence < 1.0


class BaseAgent(ABC):
    """Classe base abstrata para todos os agentes"""
    
    def __init__(self, name: str, capabilities: Union[List[AgentCapability], Set[AgentCapability]], priority: Union[AgentPriority, int] = 50):
        self.name = name
        self.capabilities = capabilities if isinstance(capabilities, set) else set(capabilities)
        # Handle both AgentPriority enum and int for Fase 2 compatibility
        if isinstance(priority, AgentPriority):
            self.priority = priority.value * 20  # Convert to numeric scale
        else:
            self.priority = priority
        self._is_active = True
        logger.info(f"Inicializando agente {name} com capacidades: {[c.value for c in self.capabilities]}")
    
    @abstractmethod  
    def can_handle(self, request) -> bool:
        """
        Verifica se o agente pode lidar com a requisição
        
        Args:
            request: AgentRequest ou contexto da conversa/sessão
            
        Returns:
            bool: True se pode processar, False caso contrário
        """
        pass
    
    @abstractmethod
    async def process(self, request) -> AgentResponse:
        """
        Processa a requisição
        
        Args:
            request: AgentRequest ou contexto completo incluindo mensagem, histórico, etc
            
        Returns:
            AgentResponse: Resposta do processamento
        """
        pass
    
    def is_active(self) -> bool:
        """Verifica se o agente está ativo"""
        return self._is_active
    
    def activate(self):
        """Ativa o agente"""
        self._is_active = True
        logger.info(f"Agente {self.name} ativado")
    
    def deactivate(self):
        """Desativa o agente"""
        self._is_active = False
        logger.info(f"Agente {self.name} desativado")
    
    def has_capability(self, capability: AgentCapability) -> bool:
        """Verifica se o agente tem uma capacidade específica"""
        return capability in self.capabilities
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(name={self.name}, priority={self.priority.name})>"


class AgentRegistry:
    """Registro central de todos os agentes disponíveis"""
    
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._capability_index: Dict[AgentCapability, List[BaseAgent]] = {}
    
    def register(self, agent: BaseAgent):
        """Registra um novo agente"""
        if agent.name in self._agents:
            logger.warning(f"Agente {agent.name} já registrado, substituindo...")
        
        self._agents[agent.name] = agent
        
        # Indexa por capacidade
        for capability in agent.capabilities:
            if capability not in self._capability_index:
                self._capability_index[capability] = []
            self._capability_index[capability].append(agent)
        
        logger.info(f"Agente {agent.name} registrado com sucesso")
    
    def unregister(self, agent_name: str):
        """Remove um agente do registro"""
        if agent_name in self._agents:
            agent = self._agents[agent_name]
            
            # Remove do índice de capacidades
            for capability in agent.capabilities:
                if capability in self._capability_index:
                    self._capability_index[capability].remove(agent)
            
            del self._agents[agent_name]
            logger.info(f"Agente {agent_name} removido do registro")
    
    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Obtém um agente pelo nome"""
        return self._agents.get(name)
    
    def get_all_agents(self) -> List[BaseAgent]:
        """Retorna todos os agentes registrados"""
        return list(self._agents.values())
    
    def get_active_agents(self) -> List[BaseAgent]:
        """Retorna apenas agentes ativos"""
        return [agent for agent in self._agents.values() if agent.is_active()]
    
    def get_agents_by_capability(self, capability: AgentCapability) -> List[BaseAgent]:
        """Retorna agentes que possuem uma capacidade específica"""
        return self._capability_index.get(capability, [])
    
    def get_agents_by_priority(self) -> List[BaseAgent]:
        """Retorna agentes ordenados por prioridade"""
        return sorted(self.get_active_agents(), key=lambda a: a.priority.value)


# Instância global do registro
agent_registry = AgentRegistry()