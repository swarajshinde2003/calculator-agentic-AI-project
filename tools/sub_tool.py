from langchain.tools import tool
from tools.number_parser import parse_numbers, fmt


@tool
def subtract_numbers(inputs: str) -> dict:
    """
    Subtracts numbers found in the input text left-to-right  (n1 - n2 - n3 ...).
    Supports integers, decimals, and negative values.

    Example Input:  "Subtract 5 and 3 from 20"  →  20 - 5 - 3
    Example Output: {"result": "12"}
    """
    numbers = parse_numbers(inputs)
    if not numbers:
        return {"error": "No numbers found. Please provide numbers to subtract."}
    if len(numbers) == 1:
        return {"result": fmt(numbers[0])}
    result = numbers[0]
    for n in numbers[1:]:
        result -= n
    return {"result": fmt(result)}

