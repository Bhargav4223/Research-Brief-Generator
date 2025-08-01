# app/utils/async_helpers.py
import asyncio
import sys
from functools import lru_cache

@lru_cache(maxsize=1)
def get_shared_event_loop():
    """Return the single event-loop for the whole process."""
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop