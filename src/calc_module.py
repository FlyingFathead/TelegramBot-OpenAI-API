# calc_module.py
#
# From:
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# https://github.com/FlyingFathead/TelegramBot-OpenAI-API
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# (updated Oct 13, 2024)

import ast
import operator
import logging
import re

# Initialize the logger
logger = logging.getLogger(__name__)

# Below are some safety measures so that the outputs aren't absolutely insane in length.
# Define maximum allowed length for the result and maximum magnitude
MAX_OUTPUT_LENGTH = 500  # Adjust as necessary
MAX_MAGNITUDE = 1e100    # Example maximum magnitude

def preprocess_expression(expression: str) -> str:
    """
    Preprocess the input expression to handle natural language constructs like 'of' and percentages.
    For example, convert '0.1% of 200000000' to '0.1 / 100 * 200000000'.
    """
    # Handle 'of' by replacing it with '*'
    expression = re.sub(r'\bof\b', '*', expression, flags=re.IGNORECASE)
    
    # Handle percentages: convert 'X%' to '(X/100)'
    expression = re.sub(r'(\d+(\.\d+)?)\s*%', r'(\1/100)', expression)
    
    logger.debug(f"Preprocessed expression: {expression}")
    return expression

def safe_eval(expression: str):
    # Replace '^' with '**' for exponentiation
    expression = expression.replace('^', '**')

    allowed_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow
    }

    def _eval(node):
        if isinstance(node, ast.BinOp):
            if type(node.op) in allowed_operators:
                left = _eval(node.left)
                right = _eval(node.right)
                op_func = allowed_operators[type(node.op)]
                result = op_func(left, right)
                
                # Logging the operation being performed
                logger.debug(f"Evaluating: {left} {type(node.op).__name__} {right} = {result}")

                # Check if the result is within acceptable magnitude
                if abs(result) > MAX_MAGNITUDE:
                    error_msg = f"Result magnitude exceeds the maximum allowed limit: {result}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                return result
            else:
                error_msg = f"Unsupported operation: {type(node.op).__name__}"
                logger.error(error_msg)
                raise ValueError(error_msg)
        elif isinstance(node, ast.Num):
            logger.debug(f"Numeric literal: {node.n}")
            return node.n
        elif isinstance(node, ast.Expression):
            return _eval(node.body)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            operand = _eval(node.operand)
            if isinstance(node.op, ast.UAdd):
                return +operand
            elif isinstance(node.op, ast.USub):
                return -operand
        else:
            error_msg = f"Unsupported type: {type(node).__name__}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    try:
        node = ast.parse(expression, mode='eval')
        logger.info(f"Parsed expression: {expression}")
        return _eval(node.body)
    except Exception as e:
        logger.exception(f"Error parsing or evaluating expression: {expression}")
        raise

async def calculate_expression(expression: str):
    logger.info(f"Calculating expression: {expression}")
    try:
        # Preprocess the expression to handle 'of' and '%'
        processed_expression = preprocess_expression(expression)
        
        result = safe_eval(processed_expression)
        
        # Check if the result length is within limits
        result_str = str(result)
        if len(result_str) > MAX_OUTPUT_LENGTH:
            error_message = f"Result exceeds the maximum allowed length of {MAX_OUTPUT_LENGTH} characters."
            logger.error(error_message)
            return error_message

        # Construct the success message
        result_message = f"The result of {expression} is {result}."
        logger.info(f"Calculation successful: {result_message}")
        return result_message
    except ValueError as ve:
        # Specific handling for ValueError (e.g., unsupported operations)
        error_message = f"Error evaluating expression `{expression}`: {str(ve)}"
        logger.error(error_message)
        return error_message
    except Exception as e:
        # General error handling
        error_message = f"An unexpected error occurred while evaluating `{expression}`: {str(e)}"
        logger.error(error_message)
        return error_message
