from langchain.tools import tool
from tools.number_parser import parse_numbers, fmt


@tool
def add_numbers(inputs: str) -> dict:
    """
    Adds all numbers found in the input text.
    Supports integers, decimals, and negative values.

    Example Input:  "Add 10.5, -3, and 20"
    Example Output: {"result": "27.5"}
    """
    numbers = parse_numbers(inputs)
    if not numbers:
        return {"error": "No numbers found. Please provide numbers to add."}
    return {"result": fmt(sum(numbers))}
