import uuid
from datetime import datetime
from typing import Optional, List, Dict, Set
from dataclasses import dataclass, field
from enum import Enum
from .core import Stateful
import asyncio

class JobState(Enum):
    """Job states with valid transitions."""
    QUEUED = "QUEUED"
    BLOCKED = "BLOCKED"
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    DONE = "DONE"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"

@dataclass
class Request:
    """Base class for all requests in the system."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    status: str = "new"

class Job(Stateful):
    """Represents a unit of work with state transitions."""
    
    def __init__(self, provider_name: str, request: Request, app=None):
        """Initialize the job."""
        super().__init__(JobState.QUEUED.value)  # Initialize with QUEUED state
        self.id = str(uuid.uuid4())
        self.provider_name = provider_name
        self.request = request
        self.app = app
        self.workflow = []
        self._cost = 0.0  # Default cost
        self.estimated_cost = 0.0
        self.provider = None  # Will be set by CommandBroker
        
    def can_transition(self, new_state: str) -> bool:
        """Check if transition to new_state is valid."""
        transitions = {
            JobState.QUEUED.value: {JobState.IDLE.value, JobState.CANCELLED.value, JobState.FAILED.value},
            JobState.IDLE.value: {JobState.RUNNING.value, JobState.CANCELLED.value, JobState.FAILED.value},
            JobState.BLOCKED.value: {JobState.RUNNING.value, JobState.CANCELLED.value, JobState.FAILED.value},
            JobState.RUNNING.value: {JobState.BLOCKED.value, JobState.DONE.value, JobState.CANCELLED.value, JobState.FAILED.value},
            JobState.DONE.value: set(),
            JobState.CANCELLED.value: set(),
            JobState.FAILED.value: set(),
        }
        return new_state in transitions.get(self.state, set())

    @property
    def cost(self) -> float:
        """Get the job cost. Uses estimated cost until actual cost is known."""
        return self._cost if hasattr(self, '_cost') else self.estimated_cost
        
    @cost.setter
    def cost(self, value: float):
        """Set the actual job cost."""
        self._cost = float(value)
    
    def __str__(self):
        return f"Job({self.id}, {self.state})"
    
    def define_workflow(self, steps=None):
        """Define the workflow steps for this job."""
        # Initialize workflow steps
        self.workflow = []
        
        if steps:
            # Use provided steps
            for step in steps:
                duration = step["duration"] if isinstance(step["duration"], (int, float)) else float(step["duration"].rstrip("s"))
                self.workflow.append({
                    "action": step["action"],
                    "duration": duration
                })
        else:
            # Use default steps
            self.workflow.extend([
                {"action": "initialize", "duration": 2},
                {"action": "process", "duration": 3},
                {"action": "finalize", "duration": 1}
            ])

    async def execute_workflow(self):
        """Execute the next step in the workflow."""
        if not self.workflow:
            if self.request and self.request.command:
                await self.request.command.transition_to(CommandState.DONE)
            return

        try:
            step = self.workflow.pop(0)
            if not step:
                if self.request and self.request.command:
                    await self.request.command.transition_to(CommandState.DONE)
                return

            # Execute the step
            await asyncio.sleep(step["duration"])

            # If this was the last step and we have a command, mark it as done
            if not self.workflow and self.request and self.request.command:
                await self.request.command.transition_to(CommandState.DONE)

        except Exception as e:
            if self.request and self.request.command:
                await self.request.command.transition_to(CommandState.FAILED)
            raise

    async def process(self):
        """Process the job by executing its workflow."""
        await self.execute_workflow()

    async def execute(self):
        """Main execution loop for the job."""
        if self.state == JobState.QUEUED.value:
            await self.transition_to(JobState.IDLE.value)
            
        elif self.state == JobState.IDLE.value:
            await self.transition_to(JobState.RUNNING.value)
            await self.process()
            
            if not self.workflow:
                await self.transition_to(JobState.DONE.value)
                if self.request and self.request.command:
                    await self.request.command.transition_to(CommandState.DONE)

    async def cancel(self):
        """Cancel the job execution."""
        if self.state != JobState.DONE.value:
            await self.transition_to(JobState.CANCELLED.value)