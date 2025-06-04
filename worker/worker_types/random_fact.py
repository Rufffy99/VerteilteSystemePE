import logging
import requests

def handle(payload: str) -> str:
    """
    Fetches a random useless fact from the API and returns it.

    Parameters:
        payload (str): The input string (not used for the API but required by interface).

    Returns:
        str: A random fun fact as a string.
    """
    if not isinstance(payload, str):
        logging.error(f"Invalid payload: {payload}. Expected a string.")
        raise ValueError("Payload must be a string.")

    try:
        url = "https://uselessfacts.jsph.pl/random.json?language=de"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        fact = data.get("text", "No fact found.")
        return fact
    except requests.RequestException as e:
        logging.error(f"Request to Fun Facts API failed: {e}")
        return "Could not retrieve a fun fact at this time."