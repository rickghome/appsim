"""
Supply Chain simulation components built on the core simulation framework.
Includes factories, distribution centers, markets, and their associated actors.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import defaultdict

from .core import Message, Job, ServiceProvider, Actor

# Common Data Models

class ProductType(Enum):
    WIDGET_A = auto()
    WIDGET_B = auto()
    WIDGET_C = auto()

@dataclass
class Product:
    type: ProductType
    unit_cost: float
    production_time: int  # in simulation time units

@dataclass
class Inventory:
    products: Dict[ProductType, int] = field(default_factory=lambda: defaultdict(int))
    reserved: Dict[ProductType, int] = field(default_factory=lambda: defaultdict(int))

    def available(self, product_type: ProductType) -> int:
        return self.products[product_type] - self.reserved[product_type]

    def can_fulfill(self, product_type: ProductType, quantity: int) -> bool:
        return self.available(product_type) >= quantity

@dataclass
class Order:
    product_type: ProductType
    quantity: int
    price_per_unit: float
    buyer_id: str
    status: str = "PENDING"
    
# Factory Components

class Machine(Actor):
    """Production machine that can produce widgets."""
    VALID_STATES = ["IDLE", "SETUP", "PRODUCING", "CLEANUP", "MAINTENANCE"]
    VALID_TRANSITIONS = {
        "IDLE": ["SETUP", "MAINTENANCE"],
        "SETUP": ["PRODUCING"],
        "PRODUCING": ["CLEANUP"],
        "CLEANUP": ["IDLE"],
        "MAINTENANCE": ["IDLE"]
    }

    def __init__(self, machine_id: str, production_rate: float):
        super().__init__(f"machine_{machine_id}")
        self.production_rate = production_rate
        self.current_job = None

    async def handle_message(self, message: Message):
        if message.type == "START_PRODUCTION":
            await self.transition_to("SETUP")
            # Setup time simulation would go here
            await self.transition_to("PRODUCING")
            # Production time simulation would go here
            await self.transition_to("CLEANUP")
            await self.transition_to("IDLE")

class WidgetFactory(ServiceProvider):
    """Factory that produces widgets using machines and workers."""
    
    def __init__(self, factory_id: str):
        super().__init__(f"factory_{factory_id}")
        self.inventory = Inventory()
        self.machines: List[Machine] = []
        self.production_queue: List[Order] = []

    async def handle_command(self, command: Job):
        if command.name == "PRODUCE":
            order = command.payload["order"]
            if self._can_start_production(order):
                machine = self._get_available_machine()
                if machine:
                    await machine.send_message({
                        "type": "START_PRODUCTION",
                        "order": order
                    })
                    return True
            self.production_queue.append(order)
            return False

    def _can_start_production(self, order: Order) -> bool:
        return any(m.state == "IDLE" for m in self.machines)

    def _get_available_machine(self) -> Optional[Machine]:
        return next((m for m in self.machines if m.state == "IDLE"), None)

# Distribution Components

class Truck(Actor):
    """Delivery truck that can transport products."""
    VALID_STATES = ["IDLE", "LOADING", "IN_TRANSIT", "DELIVERING", "RETURNING"]
    VALID_TRANSITIONS = {
        "IDLE": ["LOADING"],
        "LOADING": ["IN_TRANSIT"],
        "IN_TRANSIT": ["DELIVERING"],
        "DELIVERING": ["RETURNING"],
        "RETURNING": ["IDLE"]
    }

    def __init__(self, truck_id: str, capacity: int):
        super().__init__(f"truck_{truck_id}")
        self.capacity = capacity
        self.current_load = 0
        self.route = []

class DistributionCenter(ServiceProvider):
    """Manages inventory and coordinates deliveries."""
    
    def __init__(self, dc_id: str):
        super().__init__(f"dc_{dc_id}")
        self.inventory = Inventory()
        self.trucks: List[Truck] = []
        self.delivery_queue: List[Order] = []

    async def handle_command(self, command: Job):
        if command.name == "DELIVER":
            order = command.payload["order"]
            if self.inventory.can_fulfill(order.product_type, order.quantity):
                truck = self._get_available_truck()
                if truck:
                    await truck.send_message({
                        "type": "START_DELIVERY",
                        "order": order
                    })
                    return True
            self.delivery_queue.append(order)
            return False

    def _get_available_truck(self) -> Optional[Truck]:
        return next((t for t in self.trucks if t.state == "IDLE"), None)

# Market Components

class Buyer(Actor):
    """Represents a customer that can place orders."""
    VALID_STATES = ["BROWSING", "ORDERING", "WAITING", "RECEIVING"]
    VALID_TRANSITIONS = {
        "BROWSING": ["ORDERING"],
        "ORDERING": ["WAITING"],
        "WAITING": ["RECEIVING"],
        "RECEIVING": ["BROWSING"]
    }

    def __init__(self, buyer_id: str, budget: float):
        super().__init__(f"buyer_{buyer_id}")
        self.budget = budget
        self.order_history = []

class Market(ServiceProvider):
    """Coordinates buyers, sellers, and manages transactions."""
    
    def __init__(self, market_id: str):
        super().__init__(f"market_{market_id}")
        self.buyers: List[Buyer] = []
        self.current_prices: Dict[ProductType, float] = defaultdict(float)
        self.order_book: List[Order] = []

    async def handle_command(self, command: Job):
        if command.name == "PLACE_ORDER":
            order = command.payload["order"]
            if self._validate_order(order):
                self.order_book.append(order)
                # Find best factory/DC to fulfill
                await self._route_order(order)
                return True
            return False

    def _validate_order(self, order: Order) -> bool:
        buyer = next((b for b in self.buyers if b.id == order.buyer_id), None)
        return (buyer and 
                buyer.budget >= order.quantity * order.price_per_unit)

    async def _route_order(self, order: Order):
        # This would contain logic to find best fulfillment path
        pass
