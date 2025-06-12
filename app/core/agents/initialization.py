"""
Agent system initialization and setup.
"""
import logging
from typing import List

from .registry import get_global_registry
from .question import QuestionAgent
from .chat_agent import ChatAgent
from .rag_agent import RAGAgent

logger = logging.getLogger(__name__)


async def initialize_agent_system() -> List[str]:
    """
    Initialize the complete agent system with all available agents.
    
    Returns:
        List of initialized agent names
    """
    initialized_agents = []
    
    try:
        # Get global registry
        registry = get_global_registry()
        
        # Start registry if not already started
        await registry.start()
        
        # Initialize and register Question Agent
        question_agent = QuestionAgent()
        success = registry.register(
            question_agent,
            health_check_enabled=True,
            auto_recovery=True,
            metadata={
                'initialization_time': 'startup',
                'agent_type': 'question_management',
                'phase': 3
            }
        )
        
        if success:
            initialized_agents.append(question_agent.name)
            logger.info(f"Successfully registered {question_agent.name}")
        else:
            logger.error(f"Failed to register {question_agent.name}")
        
        # Initialize and register Chat Agent
        chat_agent = ChatAgent()
        success = registry.register(
            chat_agent,
            health_check_enabled=True,
            auto_recovery=True,
            metadata={
                'initialization_time': 'startup',
                'agent_type': 'chat_conversation',
                'phase': 4
            }
        )
        
        if success:
            initialized_agents.append(chat_agent.name)
            logger.info(f"Successfully registered {chat_agent.name}")
        else:
            logger.error(f"Failed to register {chat_agent.name}")
        
        # Initialize and register RAG Agent
        rag_agent = RAGAgent()
        success = registry.register(
            rag_agent,
            health_check_enabled=True,
            auto_recovery=True,
            metadata={
                'initialization_time': 'startup',
                'agent_type': 'rag_search',
                'phase': 4
            }
        )
        
        if success:
            initialized_agents.append(rag_agent.name)
            logger.info(f"Successfully registered {rag_agent.name}")
        else:
            logger.error(f"Failed to register {rag_agent.name}")
        
        logger.info(f"Agent system initialized with {len(initialized_agents)} agents: {initialized_agents}")
        
    except Exception as e:
        logger.error(f"Error initializing agent system: {e}")
    
    return initialized_agents


async def shutdown_agent_system():
    """Shutdown the agent system gracefully."""
    try:
        registry = get_global_registry()
        await registry.stop()
        logger.info("Agent system shutdown completed")
    except Exception as e:
        logger.error(f"Error during agent system shutdown: {e}")


def get_available_agents() -> List[str]:
    """Get list of available agent types."""
    return [
        'QuestionAgent',
        'ChatAgent',
        'RAGAgent',
    ]