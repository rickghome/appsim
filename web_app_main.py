"""Main entry point for web application."""
import asyncio
from simulator.web.web import WebServer, Form, FormState
from simulator.web.types import HttpRequest, HttpResponse
from simulator.app import App
from simulator.core.observer import Observable
from simulator.core.providers import ServiceProvider
from simulator.core.state import Event
from simulator.debug.event_logger import EventLogger
import argparse

class CartServer(WebServer, ServiceProvider):
    """Example shopping cart server."""
    def __init__(self, app: App):
        WebServer.__init__(self, "cart")
        ServiceProvider.__init__(self, "cart_server")
        self.app = app
        app.register_service_provider(self)
        
    def handle_request(self, path: str, method: str, request: HttpRequest) -> HttpResponse:
        """Handle HTTP request."""
        if path == "/cart":
            if method == "POST":
                try:
                    # Create form and fill with data
                    form = Form("cart_form", "POST")
                    form.text("item_name")
                    form.text("description")
                    form.number("quantity")
                    form.number("price")
                    form.fill(request.data)
                    
                    # Process form
                    data = form.data
                    total = data["quantity"] * data["price"]
                    
                    # Create event data
                    event_data = {
                        "action": "add",
                        "item": data["item_name"],
                        "quantity": data["quantity"],
                        "price": data["price"],
                        "total": total
                    }
                    
                    # Notify observers directly
                    self.notify_observers("cart_update", event_data)
                    
                    # Also publish through message broker
                    if self.app and self.app.message_broker:
                        self.app.message_broker.publish("cart_update", self, event_data)
                    
                    return HttpResponse(200, {
                        "message": f"Added {data['quantity']} {data['item_name']} to cart",
                        "total": total
                    })
                except ValueError as e:
                    return HttpResponse(400, {"error": str(e)})
                
            elif method == "GET":
                return HttpResponse(200, {"message": "Cart contents"})
                
        return HttpResponse(404, {"error": "Not found"})
        
    async def handle_event(self, event):
        """Handle events from the service provider."""
        # We don't need to do anything here since we're just emitting events
        pass

class CartClient:
    """Client for interacting with cart server."""
    def __init__(self, server):
        self.server = server
        
    async def add_item(self, name, description, quantity, price):
        """Add an item to the cart."""
        data = {
            "item_name": name,
            "description": description,
            "quantity": quantity,
            "price": price
        }
        request = HttpRequest("POST", "/cart", data)
        return self.server.handle_request("/cart", "POST", request)
        
    async def add_random_item(self):
        """Add a random item to the cart."""
        import random
        items = [
            ("Widget", "A fancy widget", 1, 9.99),
            ("Gadget", "A cool gadget", 2, 19.99),
            ("Thing", "A useful thing", 1, 14.99),
            ("Doohickey", "A neat doohickey", 3, 4.99)
        ]
        name, desc, qty, price = random.choice(items)
        return await self.add_item(name, desc, qty, price)

async def run_app(app, cart_server, client):
    """Run the application loop."""
    await app.start()
    
    # Example: Add some items to cart
    print("\nStarting to add items to cart...")
    
    # Add items with a delay between each
    items = [
        ("Book", "An interesting book", 2, 29.99),
        ("Coffee Mug", "A large coffee mug", 1, 12.99),
        ("Laptop", "A powerful laptop", 1, 999.99)
    ]
    
    for name, desc, qty, price in items:
        await asyncio.sleep(1)  # Wait a bit between operations
        print(f"\nAdding {qty} {name}(s) to cart...")
        response = await client.add_item(name, desc, qty, price)
        print(f"Response: {response.data}")

async def main(enable_debugger: bool = False, enable_logging: bool = True, timeout: int = 15):
    """Run the web application."""
    print("\nInitializing application...")
    
    # Create and initialize the app
    app = App(enable_debugger=enable_debugger)
    
    # Create event logger if enabled
    event_logger = None
    if enable_logging:
        print("Creating event logger...")
        event_logger = EventLogger()
    
    # Create and register the cart server
    print("Registering cart server...")
    cart_server = CartServer(app)
    
    # Register event logger after cart server
    if event_logger:
        print("Registering event logger...")
        app.register_service_provider(event_logger)
        cart_server.add_observer(event_logger)  # Make sure event logger observes cart server
        
        # Subscribe to cart events through message broker
        app.message_broker.subscribe("cart_update", event_logger, event_logger.update)
    
    # Create client
    print("Creating cart client...")
    client = CartClient(cart_server)
    
    try:
        # Run app with timeout
        print("\nStarting application...")
        await asyncio.wait_for(run_app(app, cart_server, client), timeout=timeout)
    except asyncio.TimeoutError:
        print(f"\nTimeout after {timeout} seconds, shutting down...")
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        print("\nStopping application...")
        await app.stop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the web application")
    parser.add_argument("--debug", action="store_true", help="Enable debugger")
    parser.add_argument("--no-logging", action="store_true", help="Disable event logging")
    parser.add_argument("--timeout", type=int, default=15, help="Timeout in seconds (default: 15)")
    args = parser.parse_args()
    
    asyncio.run(main(
        enable_debugger=args.debug,
        enable_logging=not args.no_logging,
        timeout=args.timeout
    ))
