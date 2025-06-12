"""
Inter-agent communication system for coordinated processing.
"""
from typing import Dict, List, Optional, Any, Callable, Awaitable, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import logging
import json
from abc import ABC, abstractmethod
import uuid

from app.core.agents.base import BaseAgent, AgentResponse
from app.core.models.agent_models import AgentRequest, AgentCommunication


logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of inter-agent messages."""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    BROADCAST = "broadcast"
    DELEGATION = "delegation"
    COLLABORATION = "collaboration"
    STATUS_UPDATE = "status_update"
    ERROR = "error"


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class AgentMessage:
    """Message sent between agents."""
    message_id: str
    sender_id: str
    recipient_id: Optional[str]  # None for broadcast
    message_type: MessageType
    priority: MessagePriority = MessagePriority.NORMAL
    content: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    requires_response: bool = False
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            'message_id': self.message_id,
            'sender_id': self.sender_id,
            'recipient_id': self.recipient_id,
            'message_type': self.message_type.value,
            'priority': self.priority.value,
            'content': self.content,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'requires_response': self.requires_response,
            'correlation_id': self.correlation_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMessage':
        """Create message from dictionary."""
        return cls(
            message_id=data['message_id'],
            sender_id=data['sender_id'],
            recipient_id=data.get('recipient_id'),
            message_type=MessageType(data['message_type']),
            priority=MessagePriority(data['priority']),
            content=data.get('content', {}),
            metadata=data.get('metadata', {}),
            created_at=datetime.fromisoformat(data['created_at']),
            expires_at=datetime.fromisoformat(data['expires_at']) if data.get('expires_at') else None,
            requires_response=data.get('requires_response', False),
            correlation_id=data.get('correlation_id')
        )
    
    def is_expired(self) -> bool:
        """Check if message has expired."""
        if self.expires_at:
            return datetime.now() > self.expires_at
        return False


class MessageHandler(ABC):
    """Abstract base class for message handlers."""
    
    @abstractmethod
    async def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle incoming message and optionally return response."""
        pass
    
    @abstractmethod
    def can_handle(self, message: AgentMessage) -> bool:
        """Check if handler can process the message."""
        pass


class CommunicationBus:
    """Central communication bus for agent messaging."""
    
    def __init__(self, max_queue_size: int = 10000):
        """Initialize communication bus."""
        self.max_queue_size = max_queue_size
        
        # Message routing
        self.subscribers: Dict[str, List[Callable[[AgentMessage], Awaitable[None]]]] = {}
        self.message_handlers: Dict[str, List[MessageHandler]] = {}
        
        # Message queues per agent
        self.agent_queues: Dict[str, asyncio.Queue] = {}
        
        # Message history and tracking
        self.message_history: Dict[str, AgentMessage] = {}
        self.pending_responses: Dict[str, asyncio.Future] = {}
        
        # Statistics
        self.stats = {
            'messages_sent': 0,
            'messages_delivered': 0,
            'messages_failed': 0,
            'broadcasts_sent': 0
        }
        
        # Background tasks
        self.cleanup_task: Optional[asyncio.Task] = None
        self.running = False
    
    async def start(self):
        """Start the communication bus."""
        if self.running:
            return
        
        self.running = True
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Communication bus started")
    
    async def stop(self):
        """Stop the communication bus."""
        if not self.running:
            return
        
        self.running = False
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Cancel pending responses
        for future in self.pending_responses.values():
            if not future.done():
                future.cancel()
        
        logger.info("Communication bus stopped")
    
    def register_agent(self, agent_id: str):
        """Register an agent for communication."""
        if agent_id not in self.agent_queues:
            self.agent_queues[agent_id] = asyncio.Queue(maxsize=self.max_queue_size)
            logger.debug(f"Registered agent {agent_id} for communication")
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent from communication."""
        if agent_id in self.agent_queues:
            del self.agent_queues[agent_id]
            logger.debug(f"Unregistered agent {agent_id} from communication")
    
    def subscribe(self, 
                 agent_id: str, 
                 callback: Callable[[AgentMessage], Awaitable[None]]):
        """Subscribe to messages for an agent."""
        if agent_id not in self.subscribers:
            self.subscribers[agent_id] = []
        self.subscribers[agent_id].append(callback)
    
    def add_message_handler(self, agent_id: str, handler: MessageHandler):
        """Add message handler for an agent."""
        if agent_id not in self.message_handlers:
            self.message_handlers[agent_id] = []
        self.message_handlers[agent_id].append(handler)
    
    async def send_message(self, message: AgentMessage) -> bool:
        """Send message to recipient(s)."""
        try:
            if message.recipient_id:
                # Direct message
                return await self._send_direct_message(message)
            else:
                # Broadcast message
                return await self._send_broadcast_message(message)
        except Exception as e:
            logger.error(f"Failed to send message {message.message_id}: {e}")
            self.stats['messages_failed'] += 1
            return False
    
    async def send_request(self, 
                          sender_id: str,
                          recipient_id: str,
                          content: Dict[str, Any],
                          timeout: float = 30.0) -> Optional[AgentMessage]:
        """Send request and wait for response."""
        
        # Create request message
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_id=sender_id,
            recipient_id=recipient_id,
            message_type=MessageType.REQUEST,
            content=content,
            requires_response=True
        )
        
        # Create future for response
        future = asyncio.get_event_loop().create_future()
        self.pending_responses[message.message_id] = future
        
        try:
            # Send message
            success = await self.send_message(message)
            if not success:
                return None
            
            # Wait for response
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
            
        except asyncio.TimeoutError:
            logger.warning(f"Request {message.message_id} timed out")
            return None
        finally:
            # Cleanup
            if message.message_id in self.pending_responses:
                del self.pending_responses[message.message_id]
    
    async def send_response(self, 
                           original_message: AgentMessage,
                           sender_id: str,
                           content: Dict[str, Any]) -> bool:
        """Send response to a request message."""
        
        response = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_id=sender_id,
            recipient_id=original_message.sender_id,
            message_type=MessageType.RESPONSE,
            content=content,
            correlation_id=original_message.message_id
        )
        
        success = await self.send_message(response)
        
        # Complete pending future if exists
        if original_message.message_id in self.pending_responses:
            future = self.pending_responses[original_message.message_id]
            if not future.done():
                future.set_result(response)
        
        return success
    
    async def broadcast(self, 
                       sender_id: str,
                       content: Dict[str, Any],
                       exclude_agents: Optional[List[str]] = None) -> bool:
        """Broadcast message to all agents."""
        
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_id=sender_id,
            recipient_id=None,  # Broadcast
            message_type=MessageType.BROADCAST,
            content=content
        )
        
        return await self._send_broadcast_message(message, exclude_agents)
    
    async def get_messages(self, agent_id: str, max_messages: int = 100) -> List[AgentMessage]:
        """Get pending messages for an agent."""
        if agent_id not in self.agent_queues:
            return []
        
        queue = self.agent_queues[agent_id]
        messages = []
        
        try:
            for _ in range(min(max_messages, queue.qsize())):
                message = await asyncio.wait_for(queue.get(), timeout=0.1)
                messages.append(message)
        except asyncio.TimeoutError:
            pass
        
        return messages
    
    async def has_messages(self, agent_id: str) -> bool:
        """Check if agent has pending messages."""
        if agent_id not in self.agent_queues:
            return False
        return not self.agent_queues[agent_id].empty()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get communication bus statistics."""
        return {
            **self.stats,
            'registered_agents': len(self.agent_queues),
            'pending_messages': sum(queue.qsize() for queue in self.agent_queues.values()),
            'pending_responses': len(self.pending_responses),
            'message_history_size': len(self.message_history)
        }
    
    async def _send_direct_message(self, message: AgentMessage) -> bool:
        """Send message to specific recipient."""
        recipient_id = message.recipient_id
        
        # Store in history
        self.message_history[message.message_id] = message
        
        # Check if recipient is registered
        if recipient_id not in self.agent_queues:
            logger.warning(f"Recipient {recipient_id} not registered")
            return False
        
        # Add to recipient's queue
        queue = self.agent_queues[recipient_id]
        try:
            await queue.put(message)
            self.stats['messages_sent'] += 1
            self.stats['messages_delivered'] += 1
            
            # Notify subscribers
            await self._notify_subscribers(recipient_id, message)
            
            logger.debug(f"Message {message.message_id} delivered to {recipient_id}")
            return True
            
        except asyncio.QueueFull:
            logger.warning(f"Queue full for agent {recipient_id}")
            return False
    
    async def _send_broadcast_message(self, 
                                    message: AgentMessage,
                                    exclude_agents: Optional[List[str]] = None) -> bool:
        """Send broadcast message to all agents."""
        exclude_agents = exclude_agents or []
        
        # Store in history
        self.message_history[message.message_id] = message
        
        delivered = 0
        total_agents = 0
        
        for agent_id, queue in self.agent_queues.items():
            if agent_id in exclude_agents or agent_id == message.sender_id:
                continue
            
            total_agents += 1
            
            try:
                await queue.put(message)
                delivered += 1
                
                # Notify subscribers
                await self._notify_subscribers(agent_id, message)
                
            except asyncio.QueueFull:
                logger.warning(f"Queue full for agent {agent_id}")
        
        self.stats['broadcasts_sent'] += 1
        self.stats['messages_sent'] += 1
        self.stats['messages_delivered'] += delivered
        
        logger.debug(f"Broadcast {message.message_id} delivered to {delivered}/{total_agents} agents")
        return delivered > 0
    
    async def _notify_subscribers(self, agent_id: str, message: AgentMessage):
        """Notify subscribers of new message."""
        subscribers = self.subscribers.get(agent_id, [])
        
        for callback in subscribers:
            try:
                await callback(message)
            except Exception as e:
                logger.error(f"Subscriber callback error for {agent_id}: {e}")
    
    async def _cleanup_loop(self):
        """Background cleanup task."""
        while self.running:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                await self._cleanup_expired_messages()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
    
    async def _cleanup_expired_messages(self):
        """Remove expired messages from history."""
        current_time = datetime.now()
        expired_ids = []
        
        for message_id, message in self.message_history.items():
            if message.is_expired():
                expired_ids.append(message_id)
            elif (current_time - message.created_at).days > 1:  # Remove old messages
                expired_ids.append(message_id)
        
        for message_id in expired_ids:
            del self.message_history[message_id]
        
        if expired_ids:
            logger.debug(f"Cleaned up {len(expired_ids)} expired messages")


class CollaborationManager:
    """Manager for agent collaboration and coordination."""
    
    def __init__(self, communication_bus: CommunicationBus):
        """Initialize collaboration manager."""
        self.communication_bus = communication_bus
        self.active_collaborations: Dict[str, Dict[str, Any]] = {}
        
    async def initiate_collaboration(self,
                                   initiator_id: str,
                                   participants: List[str],
                                   collaboration_type: str,
                                   context: Dict[str, Any]) -> str:
        """Initiate a new collaboration session."""
        
        collaboration_id = str(uuid.uuid4())
        
        # Create collaboration context
        collaboration_context = {
            'id': collaboration_id,
            'type': collaboration_type,
            'initiator': initiator_id,
            'participants': participants,
            'context': context,
            'created_at': datetime.now(),
            'status': 'active',
            'messages': []
        }
        
        self.active_collaborations[collaboration_id] = collaboration_context
        
        # Notify participants
        for participant in participants:
            if participant != initiator_id:
                message = AgentMessage(
                    message_id=str(uuid.uuid4()),
                    sender_id=initiator_id,
                    recipient_id=participant,
                    message_type=MessageType.COLLABORATION,
                    content={
                        'action': 'invite',
                        'collaboration_id': collaboration_id,
                        'collaboration_type': collaboration_type,
                        'context': context
                    }
                )
                
                await self.communication_bus.send_message(message)
        
        logger.info(f"Initiated collaboration {collaboration_id} with {len(participants)} participants")
        return collaboration_id
    
    async def send_collaboration_message(self,
                                       collaboration_id: str,
                                       sender_id: str,
                                       content: Dict[str, Any]) -> bool:
        """Send message within collaboration context."""
        
        if collaboration_id not in self.active_collaborations:
            return False
        
        collaboration = self.active_collaborations[collaboration_id]
        
        if sender_id not in collaboration['participants']:
            return False
        
        # Create collaboration message
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_id=sender_id,
            recipient_id=None,  # Broadcast to collaboration
            message_type=MessageType.COLLABORATION,
            content={
                'collaboration_id': collaboration_id,
                'message_content': content
            }
        )
        
        # Send to all participants except sender
        participants = [p for p in collaboration['participants'] if p != sender_id]
        success_count = 0
        
        for participant in participants:
            message.recipient_id = participant
            if await self.communication_bus.send_message(message):
                success_count += 1
        
        # Store in collaboration history
        collaboration['messages'].append({
            'sender': sender_id,
            'content': content,
            'timestamp': datetime.now().isoformat()
        })
        
        return success_count > 0
    
    async def end_collaboration(self, collaboration_id: str, initiator_id: str) -> bool:
        """End an active collaboration."""
        
        if collaboration_id not in self.active_collaborations:
            return False
        
        collaboration = self.active_collaborations[collaboration_id]
        
        if collaboration['initiator'] != initiator_id:
            return False
        
        # Notify participants
        for participant in collaboration['participants']:
            if participant != initiator_id:
                message = AgentMessage(
                    message_id=str(uuid.uuid4()),
                    sender_id=initiator_id,
                    recipient_id=participant,
                    message_type=MessageType.COLLABORATION,
                    content={
                        'action': 'end',
                        'collaboration_id': collaboration_id
                    }
                )
                
                await self.communication_bus.send_message(message)
        
        # Mark as ended
        collaboration['status'] = 'ended'
        collaboration['ended_at'] = datetime.now()
        
        logger.info(f"Ended collaboration {collaboration_id}")
        return True


class DelegationManager:
    """Manager for task delegation between agents."""
    
    def __init__(self, communication_bus: CommunicationBus):
        """Initialize delegation manager."""
        self.communication_bus = communication_bus
        self.active_delegations: Dict[str, Dict[str, Any]] = {}
    
    async def delegate_task(self,
                           delegator_id: str,
                           delegate_id: str,
                           task_description: str,
                           task_data: Dict[str, Any],
                           timeout: float = 60.0) -> Optional[Dict[str, Any]]:
        """Delegate a task to another agent."""
        
        delegation_id = str(uuid.uuid4())
        
        # Create delegation context
        delegation_context = {
            'id': delegation_id,
            'delegator': delegator_id,
            'delegate': delegate_id,
            'task_description': task_description,
            'task_data': task_data,
            'created_at': datetime.now(),
            'status': 'pending'
        }
        
        self.active_delegations[delegation_id] = delegation_context
        
        # Send delegation request
        response = await self.communication_bus.send_request(
            sender_id=delegator_id,
            recipient_id=delegate_id,
            content={
                'action': 'delegate',
                'delegation_id': delegation_id,
                'task_description': task_description,
                'task_data': task_data
            },
            timeout=timeout
        )
        
        if response:
            delegation_context['status'] = 'completed'
            delegation_context['result'] = response.content
            logger.info(f"Delegation {delegation_id} completed successfully")
            return response.content
        else:
            delegation_context['status'] = 'failed'
            logger.warning(f"Delegation {delegation_id} failed")
            return None


# Global communication bus instance
_global_bus: Optional[CommunicationBus] = None
_bus_lock = asyncio.Lock()


async def get_global_communication_bus() -> CommunicationBus:
    """Get or create global communication bus."""
    global _global_bus
    
    async with _bus_lock:
        if _global_bus is None:
            _global_bus = CommunicationBus()
            await _global_bus.start()
        return _global_bus


async def stop_global_communication_bus():
    """Stop the global communication bus."""
    global _global_bus
    
    if _global_bus:
        await _global_bus.stop()
        _global_bus = None