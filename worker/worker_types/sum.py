

def handle(payload):
    """
    Expects a list of numbers and returns their sum.
    """
    if not isinstance(payload, list):
        raise ValueError("Payload must be a list of numbers.")
    return sum(payload)