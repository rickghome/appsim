"""Command management."""
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
from .state import Stateful
from .job import Job

class CommandState(Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    ACCEPTED = "ACCEPTED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    REJECTED = "REJECTED"

class Command(Stateful):
    """A command that can be executed by a service provider."""
    
    def __init__(self, name: str, payload: Dict[str, Any] = None, app=None):
        """
        Initialize a command.
        
        :param name: Name of the command
        :param payload: Dictionary of command parameters
        :param app: Optional App instance for command broker access
        """
        super().__init__(CommandState.PENDING.value)  # Initialize state with PENDING
        self.name = name
        self.payload = payload or {}
        self.id = str(uuid.uuid4())
        self.timestamp = datetime.now()
        self.app = app
        self.result = None
        self.job = None  # Store associated job

    def __str__(self):
        return f"Command({self.name}, {self.state})"
        
    def can_transition(self, new_state: str) -> bool:
        """Check if transition to new_state is valid."""
        transitions = {
            CommandState.PENDING.value: {CommandState.QUEUED.value, CommandState.REJECTED.value},
            CommandState.QUEUED.value: {CommandState.ACCEPTED.value, CommandState.REJECTED.value},
            CommandState.ACCEPTED.value: {CommandState.RUNNING.value, CommandState.FAILED.value},
            CommandState.RUNNING.value: {CommandState.DONE.value, CommandState.FAILED.value},
            CommandState.DONE.value: set(),
            CommandState.FAILED.value: set(),
            CommandState.REJECTED.value: set()
        }
        return new_state in transitions.get(self.state, set())
        
    async def submit(self):
        """Submit this command to the app's command broker"""
        if self.app:
            await self.app.command_broker.submit_command(self)
        else:
            raise RuntimeError("Cannot submit command - no app reference")
            
    async def wait_for_completion(self):
        """Wait for the command to reach a terminal state."""
        while self.state not in {CommandState.DONE.value, CommandState.FAILED.value, CommandState.REJECTED.value}:
            await asyncio.sleep(0.1)  # Small delay to avoid busy waiting
        return self

class CommandBroker:
    """Matches commands with service providers."""
    def __init__(self, app):
        self.app = app
        self.service_providers = []
        self.command_queue = asyncio.Queue()
        self.broker_task = None
        self.running = False  # Flag to track if the broker is running
        self._commands = {}  # Store commands by ID
        
    async def start(self):
        """Start processing commands."""
        self.running = True
        self.broker_task = asyncio.create_task(self._process_commands())
        
    async def _process_commands(self):
        """Continuously process incoming commands."""
        while self.running:
            try:
                command = await self.command_queue.get()
                await self._process_command(command)
            except Exception as e:
                # Just raise the exception since events will capture it
                raise
                
    async def _process_command(self, command: Command):
        """Process a command by collecting jobs from providers and selecting the best one."""
        jobs = await self._collect_jobs(command)
        if jobs:
            best_job = self._select_best_job(jobs)
            await self._accept_command(command, best_job)
        else:
            await self._reject_command(command)
            
    async def shutdown(self):
        """Shut down the broker."""
        self.running = False
        if self.broker_task:
            await self.broker_task
            
    def register_service_provider(self, service_provider):
        """Register a service provider with the broker."""
        self.service_providers.append(service_provider)
        
    def find_provider_for_command(self, command):
        """Find a provider that can handle this command."""
        for provider in self.service_providers:
            if provider.can_handle_command(command):
                return provider
        return None
        
    async def submit_command(self, command):
        """Submit a command to the broker."""
        command.transition_to(CommandState.QUEUED.value)
        self._commands[command.id] = command
        await self.command_queue.put(command)
        
    def get_job_for_command(self, command_id):
        """Get the job associated with a command."""
        command = self._commands.get(command_id)
        return command.job if command else None
        
    async def _accept_command(self, command: Command, job: Job):
        """Accept the command and schedule the job."""
        command.transition_to(CommandState.ACCEPTED.value)
        command.job = job
        await job.provider.handle_command(command)
        
    async def _reject_command(self, command: Command):
        """Reject the command when no service provider can handle it."""
        command.transition_to(CommandState.REJECTED.value)
        
    async def _collect_jobs(self, command: Command) -> List[Job]:
        """Collect jobs from all providers that can handle this command."""
        jobs = []
        for provider in self.service_providers:
            if provider.can_handle_command(command):
                job = await provider.create_command(command)
                if job:
                    job.provider = provider  # Set the provider reference
                    jobs.append(job)
        return jobs
        
    def _select_best_job(self, jobs):
        """Select the best job from available options, prioritizing lowest cost."""
        return min(jobs, key=lambda j: j.cost) if jobs else None

class CommandGenerator:
    """Spawns simulated commands automatically on a background asyncio task."""
    
    def __init__(self, app, command_type, interval_range=(5, 30), **params):
        self.app = app
        self.command_type = command_type
        self.interval_range = interval_range
        self.params = params
        self.running = True
        self.task = asyncio.create_task(self._run())
        
        self.app.command_generators.append(self) # auto-reg with app...

    async def _run(self):
        """Continuously generate and submit commands until stopped."""
        try:
            while self.running and self.app.running:  # Stop if app shuts down
                command = self.command_type(**self.params)
                await self.app.command_broker.submit_command(command)
                await asyncio.sleep(self._get_random_delay())
        except asyncio.CancelledError:
            pass  # Graceful exit on cancellation

    async def stop(self):
        """Stops the command generator gracefully."""
        self.running = False
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task  
            except asyncio.CancelledError:
                pass  # Handle graceful shutdown

    def _get_random_delay(self):
        return random.uniform(*self.interval_range) / self.app.time_manager.simulation_speed