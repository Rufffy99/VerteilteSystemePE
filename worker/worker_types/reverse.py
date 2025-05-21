

def handle(payload):
    """
    Reverses a given string payload.

    Args:
        payload (str): The string to reverse.

    Returns:
        str: The reversed string.
    """
    if not isinstance(payload, str):
        raise ValueError("Payload must be a string.")
    return payload[::-1]