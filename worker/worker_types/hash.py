import hashlib
import logging

def handle(payload: str) -> str:
    """
    Computes the SHA256 hash of the given payload.

    Parameters:
        payload (str): The input string to hash.

    Returns:
        str: The hexadecimal SHA256 hash of the payload.
    """
    if not isinstance(payload, str):
        logging.error(f"Invalid payload: {payload}. Expected a string.")
        raise ValueError("Payload must be a string.")
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()