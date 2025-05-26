import time
import logging

def handle(payload: float) -> str:
    """
    Introduces an artificial delay for load balancing or testing purposes.

    Parameters:
        payload (float or int): The number of seconds to wait.

    Returns:
        str: Confirmation message after waiting.
    """
    try:
        delay = float(payload)
        if delay < 0:
            logging.error(f"Negative delay: {delay}. Expected a non-negative number.")
            raise ValueError("Payload must be a non-negative number representing seconds to wait.")
        time.sleep(delay)
        return f"Waited for {delay} seconds"
    except ValueError:
        logging.error(f"Invalid payload: {payload}. Expected a number.")
        raise ValueError("Payload must be a number representing seconds to wait.")
    