from langchain.tools import tool
from functools import reduce
import operator
from tools.number_parser import parse_numbers, fmt


@tool
def multiply_numbers(inputs: str) -> dict:
    """
    Multiplies all numbers found in the input text.
    Supports integers, decimals, and negative values.

    Example Input:  "Multiply 3, 4, and 5"
    Example Output: {"result": "60"}
    """
    numbers = parse_numbers(inputs)
    if not numbers:
        return {"error": "No numbers found. Please provide numbers to multiply."}
    result = reduce(operator.mul, numbers, 1.0)
    return {"result": fmt(result)}
