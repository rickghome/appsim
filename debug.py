import traceback
import sys
import asyncio
import logging
from main import main

# Set up logging
logging.basicConfig(level=logging.DEBUG)

try:
    main()
except Exception as e:
    print("\nError:", str(e))
    print("\nFull traceback:")
    traceback.print_exc(file=sys.stdout)
    
    # Print all running tasks
    loop = asyncio.get_event_loop()
    tasks = asyncio.all_tasks(loop)
    print("\nRunning tasks at time of error:")
    for task in tasks:
        if hasattr(task, 'created_at'):
            print(f"- {task.get_name()} (created at {task.created_at})")
        else:
            print(f"- {task.get_name()}")
