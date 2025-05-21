

import time

def handle(payload):
    """
    Introduces an artificial delay for load balancing or testing purposes.

    Parameters:
        payload (float or int): The number of seconds to wait.

    Returns:
        str: Confirmation message after waiting.
    """
    delay = float(payload)
    time.sleep(delay)
    return f"Waited for {delay} seconds"