"""
Agent registry for discovery, management, and lifecycle control.
"""
from typing import Dict, List, Set, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import asyncio
import logging
from enum import Enum
import threading
from collections import defaultdict

from app.core.agents.base import BaseAgent, AgentCapability
from app.core.models.agent_models import AgentMetrics


logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent status in the registry."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISABLED = "disabled"
    ERROR = "error"
    MAINTENANCE = "maintenance"


@dataclass
class AgentRegistration:
    """Agent registration information."""
    agent: BaseAgent
    status: AgentStatus = AgentStatus.ACTIVE
    registered_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    error_count: int = 0
    total_requests: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    health_check_enabled: bool = True
    auto_recovery: bool = True
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
    
    def increment_error(self):
        """Increment error count."""
        self.error_count += 1
    
    def reset_errors(self):
        """Reset error count."""
        self.error_count = 0
    
    def increment_requests(self):
        """Increment total requests."""
        self.total_requests += 1


class HealthChecker:
    """Health checker for registered agents."""
    
    def __init__(self, check_interval: int = 60):
        """Initialize health checker."""
        self.check_interval = check_interval
        self.running = False
        self.task: Optional[asyncio.Task] = None
    
    async def start(self, registry: 'AgentRegistry'):
        """Start health checking."""
        if self.running:
            return
        
        self.running = True
        self.task = asyncio.create_task(self._health_check_loop(registry))
        logger.info("Health checker started")
    
    async def stop(self):
        """Stop health checking."""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Health checker stopped")
    
    async def _health_check_loop(self, registry: 'AgentRegistry'):
        """Main health check loop."""
        while self.running:
            try:
                await asyncio.sleep(self.check_interval)
                if self.running:
                    await self._perform_health_checks(registry)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
    
    async def _perform_health_checks(self, registry: 'AgentRegistry'):
        """Perform health checks on all agents."""
        registrations = registry.get_all_registrations()
        
        for registration in registrations:
            if not registration.health_check_enabled:
                continue
            
            try:
                await self._check_agent_health(registration, registry)
            except Exception as e:
                logger.error(f"Health check failed for {registration.agent.name}: {e}")
    
    async def _check_agent_health(self, 
                                 registration: AgentRegistration, 
                                 registry: 'AgentRegistry'):
        """Check health of individual agent."""
        agent = registration.agent
        
        # Check if agent is responsive
        try:
            if hasattr(agent, 'health_check'):
                is_healthy = await agent.health_check()
            else:
                # Basic check: ensure agent is_active
                is_healthy = agent.is_active()
            
            if is_healthy:
                # Agent is healthy
                if registration.status == AgentStatus.ERROR:
                    # Recover from error state
                    if registration.auto_recovery:
                        logger.info(f"Agent {agent.name} recovered from error state")
                        registration.status = AgentStatus.ACTIVE
                        registration.reset_errors()
                
                registration.update_activity()
            else:
                # Agent is not healthy
                registration.increment_error()
                
                if registration.error_count >= 3:
                    logger.warning(f"Agent {agent.name} marked as ERROR after {registration.error_count} failures")
                    registration.status = AgentStatus.ERROR
                    
                    # Notify registry
                    await registry._handle_agent_error(registration)
        
        except Exception as e:
            logger.error(f"Health check exception for {agent.name}: {e}")
            registration.increment_error()
            
            if registration.error_count >= 5:
                registration.status = AgentStatus.ERROR


class AgentRegistry:
    """Central registry for agent discovery and management."""
    
    def __init__(self, enable_health_checks: bool = True):
        """Initialize agent registry."""
        self._registrations: Dict[str, AgentRegistration] = {}
        self._capability_index: Dict[AgentCapability, Set[str]] = defaultdict(set)
        self._priority_index: Dict[int, Set[str]] = defaultdict(set)
        self._lock = threading.RLock()
        
        # Health checking
        self.health_checker = HealthChecker() if enable_health_checks else None
        
        # Event callbacks
        self._event_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        
        # Statistics
        self._stats = {
            'total_registered': 0,
            'total_requests': 0,
            'total_errors': 0
        }
    
    async def start(self):
        """Start the registry and health checker."""
        if self.health_checker:
            await self.health_checker.start(self)
        logger.info("Agent registry started")
    
    async def stop(self):
        """Stop the registry and health checker."""
        if self.health_checker:
            await self.health_checker.stop()
        logger.info("Agent registry stopped")
    
    def register(self, 
                agent: BaseAgent, 
                health_check_enabled: bool = True,
                auto_recovery: bool = True,
                metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Register an agent in the registry."""
        with self._lock:
            if agent.name in self._registrations:
                logger.warning(f"Agent {agent.name} already registered")
                return False
            
            # Create registration
            registration = AgentRegistration(
                agent=agent,
                health_check_enabled=health_check_enabled,
                auto_recovery=auto_recovery,
                metadata=metadata or {}
            )
            
            # Store registration
            self._registrations[agent.name] = registration
            
            # Update indexes
            self._update_indexes_for_agent(agent, add=True)
            
            # Update stats
            self._stats['total_registered'] += 1
            
            logger.info(f"Registered agent: {agent.name} with capabilities: {[c.value for c in agent.capabilities]}")
            
            # Fire registration event
            self._fire_event('agent_registered', agent)
            
            return True
    
    def unregister(self, agent_name: str) -> bool:
        """Unregister an agent from the registry."""
        with self._lock:
            if agent_name not in self._registrations:
                logger.warning(f"Agent {agent_name} not found for unregistration")
                return False
            
            registration = self._registrations[agent_name]
            agent = registration.agent
            
            # Remove from indexes
            self._update_indexes_for_agent(agent, add=False)
            
            # Remove registration
            del self._registrations[agent_name]
            
            logger.info(f"Unregistered agent: {agent_name}")
            
            # Fire unregistration event
            self._fire_event('agent_unregistered', agent)
            
            return True
    
    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """Get agent by name."""
        with self._lock:
            registration = self._registrations.get(agent_name)
            return registration.agent if registration else None
    
    def get_agent_registration(self, agent_name: str) -> Optional[AgentRegistration]:
        """Get agent registration by name."""
        with self._lock:
            return self._registrations.get(agent_name)
    
    def get_agents_by_capability(self, 
                                capability: AgentCapability,
                                only_active: bool = True) -> List[BaseAgent]:
        """Get all agents with specified capability."""
        with self._lock:
            agent_names = self._capability_index.get(capability, set())
            agents = []
            
            for name in agent_names:
                registration = self._registrations.get(name)
                if registration:
                    if only_active and registration.status != AgentStatus.ACTIVE:
                        continue
                    agents.append(registration.agent)
            
            # Sort by priority
            agents.sort(key=lambda a: a.priority, reverse=True)
            return agents
    
    def get_agents_by_priority(self, 
                              min_priority: int = 0,
                              only_active: bool = True) -> List[BaseAgent]:
        """Get agents by priority range."""
        with self._lock:
            agents = []
            
            for priority, agent_names in self._priority_index.items():
                if priority >= min_priority:
                    for name in agent_names:
                        registration = self._registrations.get(name)
                        if registration:
                            if only_active and registration.status != AgentStatus.ACTIVE:
                                continue
                            agents.append(registration.agent)
            
            # Sort by priority
            agents.sort(key=lambda a: a.priority, reverse=True)
            return agents
    
    def get_all_active_agents(self) -> List[BaseAgent]:
        """Get all active agents."""
        with self._lock:
            agents = []
            for registration in self._registrations.values():
                if registration.status == AgentStatus.ACTIVE:
                    agents.append(registration.agent)
            
            # Sort by priority
            agents.sort(key=lambda a: a.priority, reverse=True)
            return agents
    
    def get_all_registrations(self) -> List[AgentRegistration]:
        """Get all agent registrations."""
        with self._lock:
            return list(self._registrations.values())
    
    def set_agent_status(self, agent_name: str, status: AgentStatus) -> bool:
        """Set agent status."""
        with self._lock:
            registration = self._registrations.get(agent_name)
            if registration:
                old_status = registration.status
                registration.status = status
                logger.info(f"Agent {agent_name} status changed: {old_status.value} -> {status.value}")
                
                # Fire status change event
                self._fire_event('agent_status_changed', registration.agent, old_status, status)
                return True
            return False
    
    def enable_agent(self, agent_name: str) -> bool:
        """Enable an agent."""
        return self.set_agent_status(agent_name, AgentStatus.ACTIVE)
    
    def disable_agent(self, agent_name: str) -> bool:
        """Disable an agent."""
        return self.set_agent_status(agent_name, AgentStatus.DISABLED)
    
    def get_agent_status(self, agent_name: str) -> Optional[AgentStatus]:
        """Get agent status."""
        with self._lock:
            registration = self._registrations.get(agent_name)
            return registration.status if registration else None
    
    def record_agent_request(self, agent_name: str):
        """Record that an agent processed a request."""
        with self._lock:
            registration = self._registrations.get(agent_name)
            if registration:
                registration.increment_requests()
                registration.update_activity()
                self._stats['total_requests'] += 1
    
    def record_agent_error(self, agent_name: str):
        """Record that an agent had an error."""
        with self._lock:
            registration = self._registrations.get(agent_name)
            if registration:
                registration.increment_error()
                self._stats['total_errors'] += 1
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        with self._lock:
            active_count = sum(1 for r in self._registrations.values() 
                             if r.status == AgentStatus.ACTIVE)
            
            return {
                'total_agents': len(self._registrations),
                'active_agents': active_count,
                'capabilities_covered': len(self._capability_index),
                'total_registered': self._stats['total_registered'],
                'total_requests': self._stats['total_requests'],
                'total_errors': self._stats['total_errors'],
                'error_rate': (self._stats['total_errors'] / max(self._stats['total_requests'], 1))
            }
    
    def get_agent_metrics(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get metrics for specific agent."""
        with self._lock:
            registration = self._registrations.get(agent_name)
            if registration:
                agent_stats = {
                    'name': agent_name,
                    'status': registration.status.value,
                    'registered_at': registration.registered_at.isoformat(),
                    'last_activity': registration.last_activity.isoformat(),
                    'error_count': registration.error_count,
                    'total_requests': registration.total_requests,
                    'capabilities': [c.value for c in registration.agent.capabilities],
                    'priority': registration.agent.priority
                }
                
                # Add agent-specific metrics if available
                if hasattr(registration.agent, 'get_metrics'):
                    try:
                        agent_metrics = registration.agent.get_metrics()
                        agent_stats['agent_metrics'] = agent_metrics
                    except Exception as e:
                        logger.warning(f"Could not get metrics for {agent_name}: {e}")
                
                return agent_stats
            return None
    
    def search_agents(self, 
                     query: str,
                     capabilities: Optional[List[AgentCapability]] = None,
                     min_priority: int = 0,
                     only_active: bool = True) -> List[BaseAgent]:
        """Search agents by various criteria."""
        with self._lock:
            candidates = []
            
            for registration in self._registrations.values():
                agent = registration.agent
                
                # Status filter
                if only_active and registration.status != AgentStatus.ACTIVE:
                    continue
                
                # Priority filter
                if agent.priority < min_priority:
                    continue
                
                # Capability filter
                if capabilities:
                    if not any(cap in agent.capabilities for cap in capabilities):
                        continue
                
                # Text search in name
                if query.lower() in agent.name.lower():
                    candidates.append((agent, 1.0))  # Exact name match
                    continue
                
                # Text search in capabilities
                capability_text = ' '.join(cap.value for cap in agent.capabilities)
                if query.lower() in capability_text.lower():
                    candidates.append((agent, 0.5))  # Capability match
            
            # Sort by relevance and priority
            candidates.sort(key=lambda x: (x[1], x[0].priority), reverse=True)
            
            return [agent for agent, score in candidates]
    
    def register_event_callback(self, event_type: str, callback: Callable):
        """Register callback for registry events."""
        self._event_callbacks[event_type].append(callback)
    
    def unregister_event_callback(self, event_type: str, callback: Callable):
        """Unregister event callback."""
        if callback in self._event_callbacks[event_type]:
            self._event_callbacks[event_type].remove(callback)
    
    async def _handle_agent_error(self, registration: AgentRegistration):
        """Handle agent error state."""
        logger.warning(f"Handling error state for agent {registration.agent.name}")
        
        # Try to restart agent if it supports it
        if hasattr(registration.agent, 'restart'):
            try:
                await registration.agent.restart()
                logger.info(f"Successfully restarted agent {registration.agent.name}")
                registration.status = AgentStatus.ACTIVE
                registration.reset_errors()
            except Exception as e:
                logger.error(f"Failed to restart agent {registration.agent.name}: {e}")
    
    def _update_indexes_for_agent(self, agent: BaseAgent, add: bool = True):
        """Update capability and priority indexes for agent."""
        if add:
            # Add to capability index
            for capability in agent.capabilities:
                self._capability_index[capability].add(agent.name)
            
            # Add to priority index
            self._priority_index[agent.priority].add(agent.name)
        else:
            # Remove from capability index
            for capability in agent.capabilities:
                self._capability_index[capability].discard(agent.name)
            
            # Remove from priority index
            self._priority_index[agent.priority].discard(agent.name)
    
    def _fire_event(self, event_type: str, *args, **kwargs):
        """Fire registry event to registered callbacks."""
        for callback in self._event_callbacks[event_type]:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Event callback error for {event_type}: {e}")


class DistributedAgentRegistry:
    """Distributed version of agent registry for multi-instance deployments."""
    
    def __init__(self, node_id: str, discovery_backend: Optional[Any] = None):
        """Initialize distributed registry."""
        self.node_id = node_id
        self.local_registry = AgentRegistry()
        self.discovery_backend = discovery_backend
        self.remote_nodes: Dict[str, Dict[str, Any]] = {}
        
        # Synchronization
        self.sync_interval = 30  # seconds
        self.sync_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start distributed registry."""
        await self.local_registry.start()
        
        if self.discovery_backend:
            self.sync_task = asyncio.create_task(self._sync_loop())
        
        logger.info(f"Distributed registry started for node {self.node_id}")
    
    async def stop(self):
        """Stop distributed registry."""
        if self.sync_task:
            self.sync_task.cancel()
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass
        
        await self.local_registry.stop()
        logger.info(f"Distributed registry stopped for node {self.node_id}")
    
    def register_local(self, agent: BaseAgent, **kwargs) -> bool:
        """Register agent locally."""
        success = self.local_registry.register(agent, **kwargs)
        
        if success and self.discovery_backend:
            # Publish to distributed backend
            asyncio.create_task(self._publish_agent(agent))
        
        return success
    
    def get_all_agents(self, include_remote: bool = True) -> List[BaseAgent]:
        """Get all agents (local and remote)."""
        local_agents = self.local_registry.get_all_active_agents()
        
        if not include_remote or not self.discovery_backend:
            return local_agents
        
        # TODO: Add remote agent proxies
        return local_agents
    
    async def _sync_loop(self):
        """Synchronization loop for distributed discovery."""
        while True:
            try:
                await asyncio.sleep(self.sync_interval)
                await self._sync_with_remote()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Sync error: {e}")
    
    async def _sync_with_remote(self):
        """Sync with remote registry nodes."""
        # TODO: Implement distributed synchronization
        pass
    
    async def _publish_agent(self, agent: BaseAgent):
        """Publish agent to distributed backend."""
        # TODO: Implement agent publishing
        pass


# Global registry instance
_global_registry: Optional[AgentRegistry] = None
_registry_lock = threading.Lock()


def get_global_registry() -> AgentRegistry:
    """Get or create global agent registry."""
    global _global_registry
    
    with _registry_lock:
        if _global_registry is None:
            _global_registry = AgentRegistry()
        return _global_registry


async def start_global_registry():
    """Start the global agent registry."""
    registry = get_global_registry()
    await registry.start()


async def stop_global_registry():
    """Stop the global agent registry."""
    global _global_registry
    
    if _global_registry:
        await _global_registry.stop()
        _global_registry = None