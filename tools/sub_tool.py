from langchain.tools import tool

@tool
def subtract_numbers(inputs: str) -> dict:
    """
    Extract integers from a text string and subtract them sequentially.

    The function reads a string containing numbers mixed with words or symbols,
    extracts all valid integers, and performs subtraction in order:
    
        result = n1 - n2 - n3 - ...
        
    Parameters:
    ----------
    inputs : str
        A string containing integers separated by spaces, commas, or text.
        
    Returns:
    -------
    dict
        A dictionary with key:
        - "result": int — the subtraction result.

    Examples:
    ---------
    Input:
        "10 20 30 and four"
    Output:
        {"result": -40}
    Notes:
    ------
    - Non-numeric words are ignored.
    - If only one number is found, it is returned as-is.
    - If no numbers are found, the result is 0.
    """
    numbers = [int(num) for num in inputs.replace(",", "").split() if num.isdigit()]

    if not numbers:
        return {"result": 0}

    result = numbers[0]
    for num in numbers[1:]:
        result -= num

    return {"result": result}

