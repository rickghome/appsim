"""Main application class that coordinates all components."""
import asyncio
from .utils import MessageBroker, TimeManager
from .core import ServiceProvider, Job, JobState, Request, Command, CommandState, CommandBroker, CommandGenerator
from .debug import Debugger
from .debug.event_logger import EventLogger
from typing import Optional, List
from .core.providers import ServiceProviderState

class App(ServiceProvider):
    """Main application class that coordinates all components."""
    def __init__(self, enable_debugger: bool = False):
        # Initialize as ServiceProvider
        super().__init__("app")
        self.app = self  # Set app reference directly since we are the app
        
        self.message_broker = self.make_message_broker()
        self.time_manager = TimeManager()
        self.command_broker = CommandBroker(self)
        self.command_generators: List[CommandGenerator] = []
        self.service_providers: List[ServiceProvider] = []
        self.dashboard_enabled = False
        self.running = False
        
        # Initialize debugger if enabled
        self.debugger = None
        if enable_debugger:
            self.debugger = Debugger()
            self.register_service_provider(self.debugger)
            
            # Set up debugger message broker subscriptions
            self.message_broker.subscribe("state_change", self.debugger, self.debugger.handle_event)
            self.message_broker.subscribe("job_complete", self.debugger, self.debugger.handle_event)
    
    def make_message_broker(self, maxsize: int = 1000) -> MessageBroker:
        """Factory method to create a new MessageBroker instance.
        
        Args:
            maxsize: Maximum size of the message queue. Defaults to 1000.
            
        Returns:
            A new MessageBroker instance with its app field set to this App.
        """
        broker = MessageBroker(maxsize=maxsize)
        broker.app = self
        return broker

    def register_service_provider(self, service_provider):
        """Register a service provider with the application."""
        service_provider.app = self  # Set app reference during registration
        self.service_providers.append(service_provider)
        self.command_broker.register_service_provider(service_provider)
        
        # Register debugger and event logger as observers if present
        for provider in self.service_providers:
            if isinstance(provider, (Debugger, EventLogger)):
                for target in self.service_providers:
                    if target != provider:  # Don't observe yourself
                        target.add_observer(provider)
        
    def find_provider_for_command(self, command):
        """Find a provider that can handle this command"""
        return self.command_broker.find_provider_for_command(command)
    
    def set_simulation_speed(self, speed):
        """Set the simulation speed, accepting numbers or predefined labels."""
        speeds = {"fast": 720, "medium": 120, "slow": 30}

        if isinstance(speed, (int, float)):
            self.time_manager.simulation_speed = float(speed)
        elif isinstance(speed, str) and speed.lower() in speeds:
            self.time_manager.simulation_speed = speeds[speed.lower()]
        else:
            raise ValueError(f"Invalid speed: {speed}")
        
    def get_simulated_time(self):
        """Get the current simulated time."""
        return self.time_manager.get_current_time()
    
    def enable_dashboard(self):
        """Enable the dashboard for visualization."""
        self.dashboard_enabled = True
        # Dashboard initialization would go here
    
    def disable_dashboard(self):
        """Disable the dashboard."""
        self.dashboard_enabled = False
        
    async def run(self):
        """Run the application and start components."""
        if self.running:
            return
            
        try:
            await self.start()  # This will start all components
            
            # Run the event loop
            await self._run_event_loop()
            
        finally:
            await self.stop()

    async def _run_event_loop(self):
        """Run the event loop."""
        try:
            while self.running:
                # Process any pending commands
                if not self.command_broker.command_queue.empty():
                    command = await self.command_broker.command_queue.get()
                    
                    # Find provider for command
                    provider = self.find_provider_for_command(command)
                    if provider:
                        await provider.handle_command(command)
                    else:
                        pass
                        
                # Check for completed jobs
                for provider in self.service_providers:
                    for job_id, job in list(provider.jobs.items()):
                        if job.state == "DONE":
                            if job.command:
                                job.command.state = CommandState.DONE.value
                                job.command.result = job.result
                        elif job.state == "FAILED":
                            if job.command:
                                job.command.state = CommandState.FAILED.value
                                job.command.result = job.result
                                
                await asyncio.sleep(0.1)  # Prevent busy loop
                
        except Exception as e:
            self.state = ServiceProviderState.ERROR.value
            raise

    async def start(self):
        """Start the application."""
        self.running = True
        
        # Transition to WILLRUN
        self.state = ServiceProviderState.WILLRUN.value
        await asyncio.sleep(0.1)  # Give time for state change to propagate
        
        # Start message broker
        await self.message_broker.start()
        
        # Start command broker
        await self.command_broker.start()
        
        # Start all service providers
        for provider in self.service_providers:
            await provider.start()
            
        # Start our own event loop
        await super().start()
        
        # Transition to RUNNING state
        self.state = ServiceProviderState.RUNNING.value
        
        # Wait for all service providers to be RUNNING
        for provider in self.service_providers:
            while provider.state != "RUNNING":
                await asyncio.sleep(0.1)
            
    async def stop(self):
        """Stop the application and all components."""
        self.running = False
        
        # Notify observers we're about to stop
        self.notify_observers("app_stopping", {
            "message": "Application is shutting down..."
        })
        await asyncio.sleep(0.1)  # Give time for notifications to process
        
        # Stop all service providers
        for provider in self.service_providers:
            await provider.stop()
            
    async def shutdown(self):
        """Shutdown the application."""
        await self.stop()
        
    async def create_job(self, request: Request) -> Job:
        """Create a new job from a request."""
        provider = self.find_provider_for_command(request.command)
        if not provider:
            raise ValueError(f"No provider found for command: {request.command}")
            
        job = Job(request, provider)
        await provider.publish_message(job)  # Provider will handle job setup
        return job

    def can_transition(self, new_state: str) -> bool:
        """Check if transition to new_state is valid."""
        transitions = {
            ServiceProviderState.IDLE.value: {ServiceProviderState.WILLRUN.value, ServiceProviderState.ERROR.value},
            ServiceProviderState.WILLRUN.value: {ServiceProviderState.RUNNING.value, ServiceProviderState.DIDRUN.value, ServiceProviderState.ERROR.value},
            ServiceProviderState.RUNNING.value: {ServiceProviderState.PAUSED.value, ServiceProviderState.DIDRUN.value, ServiceProviderState.ERROR.value},
            ServiceProviderState.PAUSED.value: {ServiceProviderState.RUNNING.value, ServiceProviderState.ERROR.value},
            ServiceProviderState.DIDRUN.value: {ServiceProviderState.DONE.value, ServiceProviderState.ERROR.value},
            ServiceProviderState.DONE.value: {ServiceProviderState.IDLE.value},
            ServiceProviderState.ERROR.value: {ServiceProviderState.IDLE.value}
        }
        return new_state in transitions.get(self.state, set())
        
    async def submit_command(self, command: Command) -> Job:
        """Submit a command to be executed."""
        # Find provider for command
        provider = self.find_provider_for_command(command)
        if not provider:
            raise ValueError(f"No provider found for command {command.name}")
            
        # Create request and job
        request = Request(command)
        job = Job(request, provider)
        await provider.publish_message(job)  # Provider will handle job setup
        return job