"""
Pipeline processing system for agent coordination and task management.
"""
from typing import Dict, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import logging
from abc import ABC, abstractmethod
import traceback

from app.core.agents.base import BaseAgent, AgentResponse
from app.core.models.agent_models import AgentRequest, AgentTask


logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


@dataclass
class PipelineTask:
    """Task in the processing pipeline."""
    task_id: str
    request: AgentRequest
    agent: BaseAgent
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    timeout: float = 30.0
    retry_count: int = 0
    max_retries: int = 3
    result: Optional[AgentResponse] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def start(self):
        """Mark task as started."""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now()
    
    def complete(self, result: AgentResponse):
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
        self.result = result
    
    def fail(self, error: str):
        """Mark task as failed."""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now()
        self.error = error
        self.retry_count += 1
    
    def cancel(self):
        """Mark task as cancelled."""
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.now()
    
    def timeout_exceeded(self):
        """Mark task as timed out."""
        self.status = TaskStatus.TIMEOUT
        self.completed_at = datetime.now()
    
    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return (self.status in [TaskStatus.FAILED, TaskStatus.TIMEOUT] and 
                self.retry_count < self.max_retries)
    
    def reset_for_retry(self):
        """Reset task for retry."""
        self.status = TaskStatus.PENDING
        self.started_at = None
        self.completed_at = None
        self.error = None
    
    def get_execution_time(self) -> Optional[float]:
        """Get task execution time in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def get_wait_time(self) -> float:
        """Get time waiting in queue."""
        start_time = self.started_at or datetime.now()
        return (start_time - self.created_at).total_seconds()


class TaskQueue:
    """Priority queue for pipeline tasks."""
    
    def __init__(self, max_size: int = 1000):
        """Initialize task queue."""
        self.max_size = max_size
        self._tasks: List[PipelineTask] = []
        self._task_map: Dict[str, PipelineTask] = {}
        self._lock = asyncio.Lock()
        
        # Statistics
        self._stats = {
            'total_enqueued': 0,
            'total_dequeued': 0,
            'total_completed': 0,
            'total_failed': 0,
            'total_cancelled': 0,
            'total_timeout': 0
        }
    
    async def enqueue(self, task: PipelineTask) -> bool:
        """Add task to queue."""
        async with self._lock:
            if len(self._tasks) >= self.max_size:
                logger.warning(f"Task queue full, rejecting task {task.task_id}")
                return False
            
            if task.task_id in self._task_map:
                logger.warning(f"Task {task.task_id} already in queue")
                return False
            
            # Insert task in priority order
            inserted = False
            for i, existing_task in enumerate(self._tasks):
                if task.priority.value > existing_task.priority.value:
                    self._tasks.insert(i, task)
                    inserted = True
                    break
            
            if not inserted:
                self._tasks.append(task)
            
            self._task_map[task.task_id] = task
            self._stats['total_enqueued'] += 1
            
            logger.debug(f"Enqueued task {task.task_id} with priority {task.priority.value}")
            return True
    
    async def dequeue(self) -> Optional[PipelineTask]:
        """Get next task from queue."""
        async with self._lock:
            if not self._tasks:
                return None
            
            # Get highest priority task
            task = self._tasks.pop(0)
            del self._task_map[task.task_id]
            self._stats['total_dequeued'] += 1
            
            logger.debug(f"Dequeued task {task.task_id}")
            return task
    
    async def get_task(self, task_id: str) -> Optional[PipelineTask]:
        """Get task by ID."""
        async with self._lock:
            return self._task_map.get(task_id)
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel task by ID."""
        async with self._lock:
            task = self._task_map.get(task_id)
            if task and task.status == TaskStatus.PENDING:
                task.cancel()
                self._tasks.remove(task)
                del self._task_map[task_id]
                self._stats['total_cancelled'] += 1
                logger.info(f"Cancelled task {task_id}")
                return True
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        async with self._lock:
            current_size = len(self._tasks)
            priority_counts = {}
            
            for task in self._tasks:
                priority = task.priority.name
                priority_counts[priority] = priority_counts.get(priority, 0) + 1
            
            return {
                'current_size': current_size,
                'max_size': self.max_size,
                'priority_distribution': priority_counts,
                **self._stats
            }
    
    async def clear(self):
        """Clear all tasks from queue."""
        async with self._lock:
            for task in self._tasks:
                if task.status == TaskStatus.PENDING:
                    task.cancel()
            
            self._tasks.clear()
            self._task_map.clear()
            logger.info("Task queue cleared")


class WorkerPool:
    """Pool of workers for executing pipeline tasks."""
    
    def __init__(self, 
                 max_workers: int = 5,
                 worker_timeout: float = 60.0):
        """Initialize worker pool."""
        self.max_workers = max_workers
        self.worker_timeout = worker_timeout
        self.workers: List[asyncio.Task] = []
        self.running = False
        
        # Task completion callbacks
        self.completion_callbacks: List[Callable[[PipelineTask], Awaitable[None]]] = []
    
    async def start(self, task_queue: TaskQueue):
        """Start worker pool."""
        if self.running:
            return
        
        self.running = True
        self.task_queue = task_queue
        
        # Start worker tasks
        for i in range(self.max_workers):
            worker = asyncio.create_task(
                self._worker_loop(f"worker-{i}")
            )
            self.workers.append(worker)
        
        logger.info(f"Started worker pool with {self.max_workers} workers")
    
    async def stop(self):
        """Stop worker pool."""
        if not self.running:
            return
        
        self.running = False
        
        # Cancel all workers
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers to stop
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
        
        self.workers.clear()
        logger.info("Worker pool stopped")
    
    def add_completion_callback(self, callback: Callable[[PipelineTask], Awaitable[None]]):
        """Add task completion callback."""
        self.completion_callbacks.append(callback)
    
    async def _worker_loop(self, worker_id: str):
        """Main worker loop."""
        logger.info(f"Worker {worker_id} started")
        
        while self.running:
            try:
                # Get next task
                task = await self.task_queue.dequeue()
                if not task:
                    # No tasks available, wait briefly
                    await asyncio.sleep(0.1)
                    continue
                
                # Execute task
                await self._execute_task(task, worker_id)
                
                # Call completion callbacks
                for callback in self.completion_callbacks:
                    try:
                        await callback(task)
                    except Exception as e:
                        logger.error(f"Completion callback error: {e}")
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(1)  # Brief pause on error
        
        logger.info(f"Worker {worker_id} stopped")
    
    async def _execute_task(self, task: PipelineTask, worker_id: str):
        """Execute a single task."""
        logger.debug(f"Worker {worker_id} executing task {task.task_id}")
        
        task.start()
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                task.agent.process(task.request),
                timeout=task.timeout
            )
            
            task.complete(result)
            logger.debug(f"Task {task.task_id} completed successfully")
        
        except asyncio.TimeoutError:
            task.timeout_exceeded()
            logger.warning(f"Task {task.task_id} timed out after {task.timeout}s")
        
        except Exception as e:
            error_msg = f"Task execution error: {str(e)}\n{traceback.format_exc()}"
            task.fail(error_msg)
            logger.error(f"Task {task.task_id} failed: {error_msg}")


class PipelineProcessor:
    """Main pipeline processor coordinating task execution."""
    
    def __init__(self,
                 max_queue_size: int = 1000,
                 max_workers: int = 5,
                 worker_timeout: float = 60.0,
                 retry_enabled: bool = True):
        """Initialize pipeline processor."""
        self.task_queue = TaskQueue(max_size=max_queue_size)
        self.worker_pool = WorkerPool(
            max_workers=max_workers,
            worker_timeout=worker_timeout
        )
        self.retry_enabled = retry_enabled
        
        # Task tracking
        self.active_tasks: Dict[str, PipelineTask] = {}
        self.completed_tasks: Dict[str, PipelineTask] = {}
        self.max_completed_history = 1000
        
        # Performance metrics
        self.metrics = {
            'tasks_processed': 0,
            'average_execution_time': 0.0,
            'average_wait_time': 0.0,
            'success_rate': 0.0
        }
        
        # Task completion future tracking
        self.task_futures: Dict[str, asyncio.Future] = {}
    
    async def start(self):
        """Start the pipeline processor."""
        await self.worker_pool.start(self.task_queue)
        
        # Register completion callback
        self.worker_pool.add_completion_callback(self._on_task_completed)
        
        logger.info("Pipeline processor started")
    
    async def stop(self):
        """Stop the pipeline processor."""
        await self.worker_pool.stop()
        await self.task_queue.clear()
        
        # Cancel pending futures
        for future in self.task_futures.values():
            if not future.done():
                future.cancel()
        self.task_futures.clear()
        
        logger.info("Pipeline processor stopped")
    
    async def submit_task(self, 
                         request: AgentRequest,
                         agent: BaseAgent,
                         priority: TaskPriority = TaskPriority.NORMAL,
                         timeout: float = 30.0,
                         max_retries: int = 3) -> str:
        """Submit task for processing."""
        
        # Generate task ID
        task_id = f"{agent.name}_{datetime.now().timestamp()}"
        
        # Create task
        task = PipelineTask(
            task_id=task_id,
            request=request,
            agent=agent,
            priority=priority,
            timeout=timeout,
            max_retries=max_retries
        )
        
        # Enqueue task
        success = await self.task_queue.enqueue(task)
        if not success:
            raise RuntimeError("Failed to enqueue task - queue full")
        
        # Track task
        self.active_tasks[task_id] = task
        
        # Create future for result
        future = asyncio.get_event_loop().create_future()
        self.task_futures[task_id] = future
        
        logger.info(f"Submitted task {task_id} for agent {agent.name}")
        return task_id
    
    async def wait_for_task(self, task_id: str) -> AgentResponse:
        """Wait for task completion and return result."""
        future = self.task_futures.get(task_id)
        if not future:
            raise ValueError(f"Task {task_id} not found")
        
        try:
            return await future
        except asyncio.CancelledError:
            # Try to cancel the task
            await self.cancel_task(task_id)
            raise
    
    async def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get current task status."""
        # Check active tasks
        task = self.active_tasks.get(task_id)
        if task:
            return task.status
        
        # Check completed tasks
        task = self.completed_tasks.get(task_id)
        if task:
            return task.status
        
        # Check queue
        task = await self.task_queue.get_task(task_id)
        if task:
            return task.status
        
        return None
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task."""
        # Try to cancel from queue first
        if await self.task_queue.cancel_task(task_id):
            # Cancel future
            future = self.task_futures.get(task_id)
            if future and not future.done():
                future.cancel()
            return True
        
        # Check if task is active (running)
        task = self.active_tasks.get(task_id)
        if task and task.status == TaskStatus.RUNNING:
            # Can't cancel running task, but mark as cancelled
            task.cancel()
            future = self.task_futures.get(task_id)
            if future and not future.done():
                future.cancel()
            return True
        
        return False
    
    async def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get comprehensive pipeline statistics."""
        queue_stats = await self.task_queue.get_stats()
        
        return {
            'queue': queue_stats,
            'active_tasks': len(self.active_tasks),
            'completed_tasks': len(self.completed_tasks),
            'metrics': self.metrics,
            'workers': {
                'total': len(self.worker_pool.workers),
                'running': self.worker_pool.running
            }
        }
    
    async def _on_task_completed(self, task: PipelineTask):
        """Handle task completion."""
        # Move from active to completed
        if task.task_id in self.active_tasks:
            del self.active_tasks[task.task_id]
        
        # Store in completed history (with limit)
        self.completed_tasks[task.task_id] = task
        if len(self.completed_tasks) > self.max_completed_history:
            # Remove oldest completed task
            oldest_id = next(iter(self.completed_tasks))
            del self.completed_tasks[oldest_id]
        
        # Update metrics
        self._update_metrics(task)
        
        # Handle retry if needed
        if self.retry_enabled and task.can_retry():
            logger.info(f"Retrying task {task.task_id} (attempt {task.retry_count + 1})")
            task.reset_for_retry()
            await self.task_queue.enqueue(task)
            self.active_tasks[task.task_id] = task
            return
        
        # Complete future
        future = self.task_futures.get(task.task_id)
        if future and not future.done():
            if task.status == TaskStatus.COMPLETED and task.result:
                future.set_result(task.result)
            elif task.status == TaskStatus.CANCELLED:
                future.cancel()
            else:
                error_msg = task.error or f"Task failed with status {task.status.value}"
                future.set_exception(RuntimeError(error_msg))
        
        # Cleanup future
        if task.task_id in self.task_futures:
            del self.task_futures[task.task_id]
    
    def _update_metrics(self, task: PipelineTask):
        """Update performance metrics."""
        self.metrics['tasks_processed'] += 1
        
        # Update execution time
        exec_time = task.get_execution_time()
        if exec_time is not None:
            current_avg = self.metrics['average_execution_time']
            total_tasks = self.metrics['tasks_processed']
            self.metrics['average_execution_time'] = (
                (current_avg * (total_tasks - 1) + exec_time) / total_tasks
            )
        
        # Update wait time
        wait_time = task.get_wait_time()
        current_avg = self.metrics['average_wait_time']
        total_tasks = self.metrics['tasks_processed']
        self.metrics['average_wait_time'] = (
            (current_avg * (total_tasks - 1) + wait_time) / total_tasks
        )
        
        # Update success rate
        total_completed = sum(1 for t in self.completed_tasks.values() 
                            if t.status == TaskStatus.COMPLETED)
        total_tasks = len(self.completed_tasks)
        if total_tasks > 0:
            self.metrics['success_rate'] = total_completed / total_tasks


# Global pipeline processor instance
_global_processor: Optional[PipelineProcessor] = None
_processor_lock = asyncio.Lock()


async def get_global_processor() -> PipelineProcessor:
    """Get or create global pipeline processor."""
    global _global_processor
    
    async with _processor_lock:
        if _global_processor is None:
            _global_processor = PipelineProcessor()
            await _global_processor.start()
        return _global_processor


async def stop_global_processor():
    """Stop the global pipeline processor."""
    global _global_processor
    
    if _global_processor:
        await _global_processor.stop()
        _global_processor = None