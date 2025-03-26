import re
import time
import random
import asyncio
from typing import Any, Callable, Set, Dict

class TimeManager:
    """Manages simulation time scaling."""
    time_units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    
    def __init__(self):
        self.start_real_time = time.time()
        self.simulation_speed = 1  # 1:1 time ratio by default
        self.simulated_time_offset = 0
        
    def get_current_time(self):
        """Get the current simulation time."""
        elapsed_real_time = time.time() - self.start_real_time
        simulated_elapsed = elapsed_real_time * self.simulation_speed
        return self.simulated_time_offset + simulated_elapsed
    
    def convert_time_to_seconds(self, time_str):
        """Convert time format (e.g., '5m', '2h') to seconds."""
        if isinstance(time_str, (int, float)):
            return float(time_str)
        
        try:
            if isinstance(time_str, str):
                time_val, unit = time_str[:-1], time_str[-1]
                return float(time_val) * self.time_units.get(unit.strip(), 1.0)
            return float(time_str)
        except (ValueError, AttributeError):
            raise ValueError(f"Invalid time format: {time_str}")
    
    def convert_duration_range(self, duration_str):
        """Convert a duration range (e.g., "2-3m") to (min_seconds, max_seconds)."""
        if isinstance(duration_str, (int, float)):
            return float(duration_str), float(duration_str)
            
        if "-" in duration_str:
            min_str, max_str = duration_str.split("-")
            return (self.convert_time_to_seconds(min_str), 
                   self.convert_time_to_seconds(max_str))
        else:
            seconds = self.convert_time_to_seconds(duration_str)
            return seconds, seconds
    
    def get_random_duration(self, duration_str):
        """Get a random duration between min and max for a duration string."""
        min_duration, max_duration = self.convert_duration_range(duration_str)
        return random.uniform(min_duration, max_duration)
    
    def parse_speed(self, speed_str):
        """Parse a speed string (e.g., "1h=10s") into a speed factor."""
        match = re.match(r"(\d+(?:\.\d+)?)\s*([smhd])\s*=\s*(\d+(?:\.\d+)?)\s*([smhd])", speed_str)
        if match:
            sim_value, sim_unit, real_value, real_unit = match.groups()
            sim_seconds = float(sim_value) * self.time_units[sim_unit]
            real_seconds = float(real_value) * self.time_units[real_unit]
            return sim_seconds / real_seconds
        raise ValueError(f"Invalid speed format: {speed_str}")

class MessageBroker:
    """
    A publish-subscribe system for inter-component communication.
    Uses asyncio.Queue for message handling and processing.
    """
    def __init__(self, maxsize=1000):
        self.subscribers = {}
        self.queue = asyncio.Queue(maxsize=maxsize)
        self.running = True
        self.task = None
        self.app = None  # Reference to owning App instance

    def subscribe(self, channel: str, subscriber, callback: Callable):
        """Subscribe to a channel with a callback function."""
        print(f"Subscribing to channel {channel}")
        if channel not in self.subscribers:
            self.subscribers[channel] = []
        self.subscribers[channel].append((subscriber, callback))
    
    def unsubscribe(self, channel: str, subscriber):
        """Unsubscribe from a channel."""
        if channel in self.subscribers:
            self.subscribers[channel] = [
                (sub, cb) for sub, cb in self.subscribers[channel] 
                if sub != subscriber
            ]
    
    async def publish(self, channel: str, message: Any):
        """Publish a message by adding it to the queue."""
        print(f"Publishing to channel {channel}: {message}")
        if not self.task:
            await self.start()
        await self.queue.put((channel, message))
    
    async def start(self):
        """Start processing messages."""
        if not self.task or self.task.done():
            print("Starting message broker")
            self.running = True
            self.task = asyncio.create_task(self._process_queue())
    
    async def _process_queue(self):
        """Process messages asynchronously."""
        print("Message broker queue processor started")
        while self.running:
            try:
                channel, message = await self.queue.get()
                print(f"Processing message on channel {channel}")
                subscribers = self.subscribers.get(channel, [])[:]  # Copy list
                for _, callback in subscribers:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(message)
                    else:
                        callback(message)
                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error processing message: {e}")
  
    async def shutdown(self):
        """Gracefully shut down the message broker."""
        print("Shutting down message broker")
        self.running = False
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass