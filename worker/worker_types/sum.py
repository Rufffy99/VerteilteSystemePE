import logging


PayloadType = list[float | int]


def handle(payload: PayloadType) -> float:
    """
    Calculates and returns the sum of numbers from the given payload.

    The function first attempts to directly sum the payload, assuming it is an iterable of numbers.
    If a TypeError is encountered (likely because the payload is not directly iterable as numbers),
    it assumes that the payload is a comma-separated string of numbers, converts each element to a float,
    and then returns their sum.
    If any other exception occurs during processing, a ValueError is raised with an appropriate message.

    Args:
        payload (Iterable[float] or str): An iterable of numeric values or a comma-separated string of numbers.

    Returns:
        float: The sum of the numbers in the payload.

    Raises:
        ValueError: If the payload format is invalid or if an unexpected error occurs during processing.
    """


    try:
        payload_sum = sum(payload)
        return payload_sum
    except TypeError as e:
        logging.warning(f"TypeError: {e}")
        payload = [float(x) for x in payload.split(",")]
        return sum(payload)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        raise ValueError("Invalid payload format. Expected a list of numbers or a comma-separated string of numbers.")