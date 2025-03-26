# Application Architecture

## Stateful 

A Stateful object is the base class for objects that have state and can transition between states. It provides:

- A current state property
- State transition management
- State change event emission
- State validation

State transitions generate messages that are sent to the object's ServiceProvider context. This allows the ServiceProvider to orchestrate workflows based on state changes of objects within its domain.

Example state transitions might be:
- Job: QUEUED → RUNNING → DONE
- Machine: IDLE → WILLRUN → RUNNING
- Operator: READY → BUSY → DONE

## Actor

An Actor is a Stateful object that participates in Jobs within a ServiceProvider context. Actors represent resources that can perform work and transition through states. All Actors have:

- A unique ID
- A current state
- Skills/capabilities
- Availability status
- Performance metrics

### Machine Actors
Machines represent equipment or automated systems. Example: CNC Machine

States:
- IDLE: Ready for work
- WILLRUN: Setup complete, ready to start
- RUNNING: Actively processing
- DIDRUN: Processing complete
- DONE: Job finished
- ERROR: Fault condition

Attributes:
- Processing speed
- Capacity
- Maintenance schedule
- Error rates
- Setup requirements

### Human Actors
Humans represent workers or operators. Example: Machine Operator

States:
- READY: Available for work
- GET_JOB: Receiving work assignment
- SETUP_MACHINE: Preparing equipment
- START_PRODUCTION: Initiating process
- MONITOR: Supervising operation
- COLLECT_OUTPUT: Retrieving finished work
- DONE: Task complete
- BREAK: Temporarily unavailable

Attributes:
- Skill levels
- Work schedule
- Fatigue level
- Training requirements
- Performance ratings

Actors interact through:
- Job coordination
- State change events
- Resource allocation
- Performance tracking
- Error handling

## Job

A Job is a Stateful object that represents work being done in a specific ServiceProvider context. Jobs are created from Commands and have:

- A unique ID
- A state (QUEUED → IDLE → RUNNING → DONE)
- A reference to its ServiceProvider
- A set of actors involved in the job
- A workflow definition
- Results and metrics

Jobs manage:
- Coordinating multiple actors (machines, operators)
- Tracking parallel state sequences
- Managing resource allocation
- Collecting performance metrics
- Reporting progress and completion

## Command

A Command is a request to perform an action in the system. Commands are Stateful objects that transition through states as they are processed. Commands have:

- A type (what action to perform)
- Parameters (data needed for the action)
- A state (PENDING → QUEUED → ACCEPTED → RUNNING → DONE)
- A target ServiceProvider (who should handle it)
- Results (output from the action)

Commands are:
- Created by the App from user input or system needs
- Routed to appropriate ServiceProviders
- Converted into Jobs for execution
- Tracked until completion
- Used to manage system workflows

## Event

An Event is a message that represents something that happened in the system. Events are used to communicate between objects and ServiceProviders. Events have:

- A type (what kind of event)
- A source (who generated it)
- A target (optional, who should handle it)
- A payload (data relevant to the event)
- A timestamp
- A context (which ServiceProvider domain it belongs to)

Events flow through MessageBrokers and are used to:
- Notify state changes
- Request actions
- Report completion
- Signal errors or exceptions

## MessageBroker

A MessageBroker manages event flow within a ServiceProvider's context. Each ServiceProvider has its own MessageBroker that:

- Maintains a message queue
- Routes events to appropriate handlers
- Supports observer registration
- Provides message filtering
- Enables debugging and monitoring

The MessageBroker:
- Is the communication backbone for a context
- Enables loose coupling between components
- Supports async event processing
- Allows global system observation
- Facilitates debugging and logging

## ServiceProvider 

A ServiceProvider is an object that can handle commands, and has an event-loop for objects in it's context. It also has a message-broker for object interactions in it's context. A ServiceProvider can also be used as a command handler, and will then only handle commands it can handle, and not others.

A ServiceProvider knows about the App. 


## Application
The application is composed of several components that work together to provide the functionality of the application. These components are:

- The core application logic  
- The command broker
- The message broker
- The debugger 
- The event logger (vis message borker)
- Event listeners
- List of ServiceProviders 

The application is a ServiceProvider, and therefore has a main event loop. It also accepts commands (form objects or humans), and tries convert input to commands, then Job objects using ServiceProvider interface (of registered providers).


We intend that our debugger listens to all events coming through the messageborker.


## Supply Chain Components

The simulation framework includes a comprehensive supply chain modeling system that demonstrates the flexibility and power of our core architecture. This implementation shows how complex, real-world systems can be modeled using our Actor and ServiceProvider patterns.

### Component Architecture

```
Market (ServiceProvider)
├── Buyers (Actors)
├── Order Book
└── Price Engine

WidgetFactory (ServiceProvider)
├── Machines (Actors)
├── Production Queue
└── Inventory

DistributionCenter (ServiceProvider)
├── Trucks (Actors)
├── Delivery Queue
└── Warehouse Inventory
```

### Key Components

#### 1. Factory System
- **Machines**: Stateful actors that handle production
  - States: IDLE → SETUP → PRODUCING → CLEANUP
  - Managed by WidgetFactory ServiceProvider
  - Track production rates and capacity

- **Production Management**
  - Queue-based job scheduling
  - Resource allocation
  - Inventory tracking

#### 2. Distribution System
- **Trucks**: Mobile resource actors
  - States: IDLE → LOADING → IN_TRANSIT → DELIVERING → RETURNING
  - Route optimization
  - Capacity constraints

- **Warehouse Management**
  - Inventory levels
  - Order fulfillment
  - Resource scheduling

#### 3. Market System
- **Buyers**: Consumer actors
  - States: BROWSING → ORDERING → WAITING → RECEIVING
  - Budget constraints
  - Order history

- **Transaction Management**
  - Order validation
  - Price management
  - Demand tracking

### Message Flows

1. **Order Processing**
```
Buyer → Market
  → DistributionCenter (inventory check)
    → WidgetFactory (if production needed)
  → Buyer (confirmation)
```

2. **Production Flow**
```
WidgetFactory
  → Machine (start production)
    → DistributionCenter (inventory update)
      → Market (availability update)
```

3. **Delivery Flow**
```
DistributionCenter
  → Truck (assign delivery)
    → Buyer (delivery notification)
      → Market (completion update)
```

### State Management

Each component leverages our core Stateful base class:
- Explicit state definitions
- Valid state transitions
- State history tracking
- Event-driven transitions

### Resource Management

The system handles multiple resource types:
- Production capacity
- Transportation capacity
- Inventory levels
- Financial constraints

### Implementation Benefits

1. **Modularity**
   - Components are self-contained
   - Easy to extend or modify
   - Clear separation of concerns

2. **Message-Driven**
   - Asynchronous operations
   - Event-based coordination
   - Decoupled communication

3. **State Control**
   - Predictable behavior
   - Easy to monitor
   - Simple to debug

4. **Scalability**
   - Add/remove components dynamically
   - Handle multiple instances
   - Flexible resource allocation

### Example Use Cases

1. **Manufacturing**
   - Production planning
   - Resource allocation
   - Quality control

2. **Logistics**
   - Route optimization
   - Fleet management
   - Delivery scheduling

3. **Retail**
   - Inventory management
   - Order processing
   - Customer service

4. **Supply Chain**
   - Demand forecasting
   - Stock optimization
   - Cost management

## Debugger

The Debugger is both a global observer AND a ServiceProvider that manages debugging operations. 

As an observer it:
- Registers with all MessageBrokers in the system
- Receives all events and state changes
- Builds a complete view of system state
- Maintains history for replay

As a ServiceProvider it:
- Has its own message queue
- Accepts debug commands (show, step, stop, continue)
- Can control execution flow
- Can modify system state for testing
- Manages debug sessions and breakpoints

Commands it handles:
- SHOW_STATE: Display current system state
- STEP: Advance simulation by one event
- STOP: Pause at next event
- CONTINUE: Resume normal execution
- FILTER: Set context/event filters
- REPLAY: Replay from history

This dual nature allows the Debugger to both:
- Passively observe system behavior
- Actively control execution for debugging

This design allows us to:
- Debug complex workflows
- Verify system behavior
- Analyze performance
- Understand resource usage
- Validate state machines

## Roadmap

The following features are planned to enhance the simulation framework:

### 1. Time Management
- Time scaling system to control simulation speed
- Variable time steps based on activity levels
- Time warping for accelerated scenario testing
- Coordinated time management across all ServiceProviders

### 2. Metrics and Statistics
- Message broker-based metrics collection
- Performance metrics for actors and providers
  - Utilization rates
  - Queue lengths
  - Processing times
  - State transition frequencies
- Real-time statistics aggregation
- Historical trend analysis

### 3. Scenario System
- Scenario definition framework
- Environmental condition simulation
  - Time of day effects
  - Peak/off-peak behavior
  - Special events
- External factor impacts on operations
- Scenario comparison tools

### 4. Fault Injection Framework
- Simulated failures at multiple levels:
  - Actor failures (worker illness, machine breakdown)
  - Provider failures (store closure, system outage)
  - Communication failures (message loss, delays)
- Recovery scenario testing
- Resilience validation
- Degraded mode operation

### 5. Resource Management
- Provider-level capacity tracking
- Actor availability management
- Resource allocation strategies
- Constraint modeling
- Utilization optimization

### 6. Debugger Visualization
- Real-time state visualization
- Message flow tracking
- Timeline views of operations
- Performance bottleneck identification
- State transition diagrams

### 7. Event-Based State Change Notification
- Replace polling-based state monitoring with event callbacks
- Enhanced Stateful base class with async event emission
- Event bus for routing state change notifications
- Callback registration system for state listeners
- Benefits:
  - Immediate state change notification
  - Reduced system load from polling
  - More scalable state monitoring
  - Better separation of concerns
- Implementation considerations:
  - Race condition prevention
  - Event cleanup and memory management
  - Backward compatibility
  - Note: Maintain asyncio.sleep() for work simulation delays

Implementation Priority:
1. Time Management - Foundation for controlled simulation
2. Fault Injection - Critical for testing robustness
3. Metrics System - Essential for validation
4. Scenario System - Enables comprehensive testing
5. Resource Management - Supports complex workflows
6. Visualization - Aids in debugging and analysis
7. Event-Based Notification - Performance optimization