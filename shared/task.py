from dataclasses import dataclass, field
import time

@dataclass
class Task:
    """
    A class representing a task with associated metadata and processing state.
    Attributes:
        id (int): Unique identifier for the task.
        type (str): Category or type of the task.
        payload (str): Data or information required to execute the task.
        result (str): Outcome of the task processing. Defaults to an empty string.
        status (str): Current state of the task (e.g., "pending"). Defaults to "pending".
        timestamp_created (float): Unix timestamp representing when the task was created.
        timestamp_completed (float): Unix timestamp representing when the task was completed. Defaults to 0.0, indicating it has not been completed.
    """

    id: int
    type: str
    payload: str
    result: str = ""
    status: str = "pending"
    timestamp_created: float = field(default_factory=lambda: time.time())
    timestamp_completed: float = 0.0
    assigned_worker: str = None
