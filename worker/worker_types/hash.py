

import hashlib

def handle(payload):
    """
    Computes the SHA256 hash of the given payload.

    Parameters:
        payload (str): The input string to hash.

    Returns:
        str: The hexadecimal SHA256 hash of the payload.
    """
    if not isinstance(payload, str):
        raise ValueError("Payload must be a string.")
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()