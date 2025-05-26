import logging

def handle(payload: str) -> str:
    """
    Reverses a given string payload.

    Args:
        payload (str): The string to reverse.

    Returns:
        str: The reversed string.
    """
    if not isinstance(payload, str):
        logging.error(f"Invalid payload: {payload}. Expected a string.")
        raise ValueError("Payload must be a string.")
    return payload[::-1]