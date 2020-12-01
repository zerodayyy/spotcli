import re
from typing import List, Set, Union


def filter(items: List[str], query: Union[str, List[str]]) -> Set[str]:
    """Filter items in list.

    Filters items in list using full match, substring match and regex match.

    Args:
        items (List[str]): Input list.
        query (Union[str, List[str]]): Filter expression.

    Returns:
        Set[str]: Filtered items.
    """

    matches: Set[str] = set()
    if isinstance(query, str):
        query = [query]
    for query_item in query:
        # Full match
        matches = matches.union({item for item in items if query_item == item})

        # Substring match
        matches = matches.union({item for item in items if query_item in item})

        # Regular expression match
        regex = re.compile(query_item, re.IGNORECASE | re.ASCII)
        matches = matches.union({item for item in items if regex.search(item)})
    return matches
