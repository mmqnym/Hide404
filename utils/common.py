import json
import os
import glob
import hashlib

from ulid import ULID
from share.types import List


def generate_ulid() -> str:
    """
    Generate an ULID (Universally Unique Lexicographically Sortable Identifier).

    Returns:
        str: A string representation of the generated ULID.
    """

    return str(ULID())


def generate_hash(src: str | bytes) -> str:
    """
    Generate a SHA-3 256-bit hash of the given source.

    If the source is a string, it will be encoded to bytes before hashing.

    Returns:
        str: A string representation of the generated hash.
    """
    if isinstance(src, str):
        src = src.encode()

    result = hashlib.sha3_256(src)
    return result.hexdigest()


def list_all_files(directory: str) -> List[str]:
    """Get a list of all files under the given directory (recursively).

    Args:
        directory (str): The root directory to search in.

    Returns:
        List[str]: A list of paths to all files found.
    """
    file_list = glob.glob(f"{directory}/**", recursive=True)
    return [f for f in file_list if os.path.isfile(f)]

def marshall_json(data: dict) -> str:
    """
    Convert a Python dictionary into a JSON-encoded string.

    Args:
        data (dict): A dictionary to be serialized.

    Returns:
        str: A JSON-encoded string representation of the dictionary.
    """

    return json.dumps(data)

def unmarshall_json(data: str) -> dict:
    """
    Convert a JSON-encoded string into a Python dictionary.

    Args:
        data (str): A JSON-encoded string to be deserialized.

    Returns:
        dict: A dictionary representation of the JSON data.
    """

    return json.loads(data)