import json

# Constants for message types
# These constants are used to identify the type of message being sent or received.
POST_TASK = "POST_TASK"
GET_RESULT = "GET_RESULT"
RESULT_RETURN = "RESULT_RETURN"
REGISTER_WORKER = "REGISTER_WORKER"
LOOKUP_WORKER = "LOOKUP_WORKER"
DEREGISTER_WORKER = "DEREGISTER_WORKER"


def encode_message(msg_type, data):
    """
    Encodes a message consisting of a message type and associated data into a JSON formatted byte string.
    Parameters:
        msg_type (str): A string representing the type or identifier of the message.
        data (Any): The data payload of the message. This can be any JSON-serializable object.
    Returns:
        bytes: A UTF-8 encoded byte string containing the JSON representation of the message with keys "type" and "data".
    Raises:
        TypeError: If the provided data is not JSON serializable.
    """
    
    return json.dumps({
        "type": msg_type,
        "data": data
    }).encode("utf-8")


def decode_message(message_bytes):
    """
    Decodes a JSON-formatted message from a given byte sequence.
    This function attempts to decode the provided byte sequence using UTF-8 
    encoding and then parses the resulting string into a JSON object. It then 
    extracts and returns the values associated with the keys "type" and "data".
    If any error occurs during decoding or parsing, it returns None for the type 
    and a dictionary containing the error message.
    Args:
        message_bytes (bytes): The message as a sequence of bytes expected to be 
                               encoded in UTF-8 format.
    Returns:
        tuple: A tuple where the first element is the value of the "type" key 
               (or None if an exception occurs) and the second element is the value 
               of the "data" key, or a dictionary with an "error" key describing the 
               exception that occurred.
    """
    
    try:
        message_str = message_bytes.decode("utf-8")
        message = json.loads(message_str)
        return message.get("type"), message.get("data")
    except Exception as e:
        return None, {"error": str(e)}
