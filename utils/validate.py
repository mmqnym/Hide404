import re


def collection_name_rule(collection_name: str) -> None:

    # these rules are copy from langchain
    msg = (
        "Expected collection name that "
        "(1) contains 3-63 characters, "
        "(2) starts and ends with an alphanumeric character, "
        "(3) otherwise contains only alphanumeric characters, underscores or hyphens (-), "
        "(4) contains no two consecutive periods (..) and "
        "(5) is not a valid IPv4 address, "
        f"got {collection_name}"
    )
    if len(collection_name) < 3 or len(collection_name) > 63:
        raise ValueError(msg)
    if not re.match("^[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9]$", collection_name):
        raise ValueError(msg)
    if ".." in collection_name:
        raise ValueError(msg)
    if re.match("^[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}$", collection_name):
        raise ValueError(msg)
