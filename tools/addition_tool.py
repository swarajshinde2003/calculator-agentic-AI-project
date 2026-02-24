from langchain.tools import tool
import re
@tool
def add_numbers(inputs : str):
    """
    Adds a list of numbers provided in the input string.
    Parameters:
    - inputs (str): 
    string, it should contain numbers that can be extracted and summed.
    Returns:
    - dict: A dictionary with a single key "result" containing the sum of the numbers.
    Example Input:
    "Add the numbers 10, 20, and 30."
    Example Output:
    {"result": 60}
    """
    # Use regular expressions to extract all numbers from the input
    numbers = [int(num) for num in re.findall(r'\d+', inputs)]
    # numbers = [int(x) for x in inputs.replace(",", "").split() if x.isdigit()]
    
    result  = sum(numbers)
    return {"result" : result}
# print("Name: \n", add_numbers.name)
# print("Description: \n", add_numbers.description) 
# print("Args: \n", add_numbers.args) 
# test_input = "what is the sum between 10, 20 and 30 " 
# print(add_numbers.invoke(test_input))  # Example
