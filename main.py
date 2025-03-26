import asyncio
import sys
import argparse
from simulator import App, ServiceProvider, Command, Request
from simulator.jobs import Job, JobState
from simulator.commands import CommandState
import threading
from simulator.app import App
from simulator.debug.debug_ui import SimpleDebuggerUI

class ExampleServiceProvider(ServiceProvider):
    def __init__(self, name):
        super().__init__(name)
    
    def can_handle_command(self, command):
        print(f"Checking if can handle command: {command.name}")
        return command.name == "example_command"
    
    async def create_command(self, command):
        """Create a job for the command."""
        print(f"Creating job for command: {command.name}")
        # Create a job for the command
        request = Request()
        request.command = command  # Link request to command
        
        # Create a job with an estimated cost
        job = Job(self.name, request, self.app)
        job.estimated_cost = 10.0
        
        # Define workflow steps
        job.define_workflow([
            {"action": "initialize", "duration": "2s"},
            {"action": "process", "duration": "3s"},
            {"action": "finalize", "duration": "1s"}
        ])
        
        return job
    
    async def handle_command(self, command):
        """Handle the command execution."""
        print(f"Handling command {command.name}")
        try:
            # Monitor job execution - job should already exist and be linked
            job = command.job
            if not job:
                raise ValueError("No job linked to command")
                
            print(f"Monitoring job {job.id}")
            
            # Wait for job to complete
            while job.state not in [JobState.DONE.value, JobState.FAILED.value, JobState.CANCELLED.value]:
                await asyncio.sleep(0.1)
            
            # Set command result based on job state
            if job.state == JobState.DONE.value:
                command.result = {"status": "success", "job_id": job.id}
            else:
                command.result = {"status": "failed", "job_id": job.id}
                command.transition_to(CommandState.FAILED.value)
                
        except Exception as e:
            print(f"Error handling command: {e}")
            command.transition_to(CommandState.FAILED.value)
            command.result = {"error": str(e)}
    
    def create_job(self, command):
        print(f"Creating job for command: {command.name}")
        # Create a job for the command
        request = Request()
        request.command = command  # Link request to command
        
        # Create a job with an estimated cost
        job = Job(self.name, request, self.app)
        job.estimated_cost = 10.0
        
        # Define a simple workflow that demonstrates state transitions
        job.define_workflow([
            {"duration": 2.0, "action": "initialize"},
            {"duration": 3.0, "action": "process"},
            {"duration": 1.0, "action": "finalize"}
        ])
        print(f"Created job {job.id} for command {command.name}")
        return job

async def handle_job_state_change(message):
    """Handle job state change events."""
    print(f"Job state changed: {message}")


def run_simulation(app):
    """Run the simulation in a background thread."""
    asyncio.run(app.start())

def main():
    """Main entry point."""
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description='Run simulation application')
        parser.add_argument('-d', '--debug', action='store_true', help='Enable debug mode with UI')
        args = parser.parse_args()

        # Create the application
        app = App()
        
        # Set a breakpoint for the example command to reach DONE state
        app.debugger.set_breakpoint("example_command", state="DONE")
        
        # Enable visualization with 0.5s polling
        app.enable_visualization(poll_interval=0.5)
        
        # Register the example service provider
        provider = ExampleServiceProvider("example")  
        app.register_service_provider(provider)  
        
        # Create and submit an example command
        command = Command(
            name="example_command",
            payload={"data": "test"},
            app=app
        )
        
        print("\nStarting simulation...")
        
        # Start simulation in background thread
        sim_thread = threading.Thread(target=lambda: asyncio.run(app.start()))
        sim_thread.daemon = True
        sim_thread.start()
        
        # Submit command in another thread
        cmd_thread = threading.Thread(target=lambda: asyncio.run(command.submit()))
        cmd_thread.daemon = True
        cmd_thread.start()
        
        if args.debug:
            # Run debugger UI in main thread if debug mode is enabled
            print("Debug mode enabled - starting UI...")
            app.debugger.ui.run()
        else:
            # Without debug mode, just wait for command to complete
            while command.state not in [CommandState.DONE.value, CommandState.FAILED.value]:
                asyncio.run(asyncio.sleep(0.1))
        
        if args.debug:
            # Print debug information only in debug mode
            print("\nDebugger Timeline:")
            timeline = app.debugger.get_timeline()
            for event in timeline:
                print(f"[{event['timestamp']}] {event['type']} from {event['source']}")
                
            print("\nCommand State History:")
            history = app.debugger.get_component_history(command.id)
            for change in history:
                print(f"[{change['timestamp']}] {change['state_before']} -> {change['state_after']}")
        
        print("\nCleaning up...")
        asyncio.run(app.stop())
        print("Application stopped")
        
    except Exception as e:
        print(f"Error: {e}")
        raise e

if __name__ == "__main__":
    main()