"""Text-based UI for the simulation debugger."""
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
import time
import threading
import asyncio
import os

class SimpleDebuggerUI:
    """A simple text-based UI for the simulation debugger."""
    
    def __init__(self, debugger):
        self.debugger = debugger
        self.console = Console()
        self.running = True
        self._update_thread = None
        self._states = {}
        self._events = []
        self._command_ready = threading.Event()
        self._lock = threading.Lock()  # Add lock for thread safety
        
    def update_state(self, component_name: str, state: str) -> None:
        """Update the state of a component."""
        try:
            with self._lock:
                self._states[component_name] = state
                # Also log this as an event
                self._events.append(f"State update: {component_name} -> {state}")
                if len(self._events) > 100:  # Keep last 100 events
                    self._events = self._events[-100:]
        except Exception as e:
            print(f"Error updating state: {e}")
        
    def log_event(self, event_str: str) -> None:
        """Log an event."""
        try:
            with self._lock:
                self._events.append(event_str)
                if len(self._events) > 100:  # Keep last 100 events
                    self._events = self._events[-100:]
        except Exception as e:
            print(f"Error logging event: {e}")
            
    def _create_display(self) -> Layout:
        """Create the display layout."""
        try:
            layout = Layout()
            layout.split(
                Layout(name="main"),
                Layout(name="controls", size=6)
            )
            
            with self._lock:
                # Create states table
                states_table = Table(title="Component States", show_header=True, header_style="bold")
                states_table.add_column("Component", style="cyan")
                states_table.add_column("State", style="green")
                
                for component, state in sorted(self._states.items()):
                    states_table.add_row(component, state)
                    
                # Create events table
                events_table = Table(title="Recent Events", show_header=True, header_style="bold")
                events_table.add_column("Event", style="yellow")
                
                # Show last 10 events, newest first
                for event in list(reversed(self._events[-10:])):
                    events_table.add_row(event)
            
            # Create main table
            main_table = Table(show_header=False, padding=(0,1))
            main_table.add_column("States")
            main_table.add_column("Events")
            main_table.add_row(states_table, events_table)
            
            # Create controls info
            controls_table = Table(show_header=False, show_edge=False, padding=0)
            controls_table.add_column("Controls", style="bold magenta")
            controls_table.add_row("Commands:")
            controls_table.add_row("  r - Resume simulation")
            controls_table.add_row("  p - Pause simulation")
            controls_table.add_row("  s - Step through one state")
            controls_table.add_row("  q - Quit simulation")
            
            layout["main"].update(main_table)
            layout["controls"].update(controls_table)
            
            return layout
        except Exception as e:
            print(f"Error creating display: {e}")
            # Return a simple error layout
            error_layout = Layout()
            error_layout.update(f"Error creating display: {e}")
            return error_layout
        
    def _update_display(self, live: Live) -> None:
        """Update the display."""
        while self.running:
            try:
                live.update(self._create_display())
            except Exception as e:
                print(f"Error updating display: {e}")
            time.sleep(0.1)  # Update frequently
            
    def run(self) -> None:
        """Run the UI."""
        try:
            print("\n" + "="*80)
            print("SIMULATION DEBUGGER")
            print("="*80 + "\n")
            
            with Live(self._create_display(), refresh_per_second=10) as live:
                self._update_thread = threading.Thread(target=self._update_display, args=(live,))
                self._update_thread.daemon = True
                self._update_thread.start()
                
                while self.running:
                    try:
                        # Handle user input
                        cmd = input().lower()
                        if cmd == 'q':
                            self.running = False
                            break
                        elif cmd == 'r':
                            asyncio.create_task(self.debugger.resume())
                        elif cmd == 'p':
                            asyncio.create_task(self.debugger.pause())
                        elif cmd == 's':
                            asyncio.create_task(self.debugger.step())
                    except (EOFError, KeyboardInterrupt):
                        self.running = False
                        break
                    except Exception as e:
                        print(f"Error handling command: {e}")
                        continue
                        
        except Exception as e:
            print(f"Error running UI: {e}")
        finally:
            self.running = False
            if self._update_thread:
                self._update_thread.join(timeout=1.0)
