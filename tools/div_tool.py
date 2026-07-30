from langchain.tools import tool
from tools.number_parser import parse_numbers, fmt


@tool
def divide_numbers(inputs: str) -> dict:
    """
    Divides numbers found in the input text left-to-right  (n1 / n2 / n3 ...).
    Supports integers and decimals. Returns an error on division by zero.

    Example Input:  "Divide 100 by 4"
    Example Output: {"result": "25"}

    Example Input:  "What is 9 divided by 0?"
    Example Output: {"error": "Division by zero is not allowed."}
    """
    numbers = parse_numbers(inputs)
    if not numbers:
        return {"error": "No numbers found. Please provide numbers to divide."}
    if len(numbers) < 2:
        return {"error": "At least two numbers are required for division."}
    result = numbers[0]
    for n in numbers[1:]:
        if n == 0:
            return {"error": "Division by zero is not allowed."}
        result /= n
    return {"result": fmt(result)}
