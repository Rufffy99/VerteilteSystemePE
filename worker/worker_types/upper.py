

def handle(payload):
    """
    Convert the given payload to uppercase.
    Args:
        payload (str): The input string to convert.
    Returns:
        str: The uppercase version of the input string.
    Raises:
        ValueError: If payload is not a string.
    """
    
    if not isinstance(payload, str):
        raise ValueError("Payload must be a string")
    return payload.upper()