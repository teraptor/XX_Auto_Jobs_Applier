"""
Worker Module
Task processing from Redis FIFO queue
"""
from .task_worker import TaskWorker


__all__ = [
    'TaskWorker',
]
