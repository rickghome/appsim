from simulator.commands import Command
from simulator.core import StatefulEnum
import asyncio

async def main():
    # Create a command
    command = Command("test_command", {"data": "test"})
    print(f"Initial state: {command.state}")  # Should be PENDING
    
    # This should work - valid transition
    command.transition_to("QUEUED")
    print(f"After QUEUED: {command.state}")
    
    # This will fail - can't go from QUEUED to RUNNING
    # Must go QUEUED -> ACCEPTED -> RUNNING
    try:
        command.transition_to("RUNNING")
    except ValueError as e:
        print(f"Error: {e}")
    
    # Show the correct path
    print("\nCorrect transition path:")
    command.transition_to("ACCEPTED")
    print(f"After ACCEPTED: {command.state}")
    command.transition_to("RUNNING")
    print(f"After RUNNING: {command.state}")
    command.transition_to("DONE")
    print(f"After DONE: {command.state}")
    
    # Try to transition from DONE (should fail)
    try:
        command.transition_to("RUNNING")
    except ValueError as e:
        print(f"\nError transitioning from DONE: {e}")

if __name__ == "__main__":
    asyncio.run(main())
