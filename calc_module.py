# calc_module.py

import ast
import operator
import logging

# Initialize the logger
logger = logging.getLogger(__name__)

# Below are some safety measures so that the outputs aren't absolutely insane in length.
# Define maximum allowed length for the result and maximum magnitude
MAX_OUTPUT_LENGTH = 100  # Adjust as necessary
MAX_MAGNITUDE = 1e100    # Example maximum magnitude

def safe_eval(expression):
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
        result = safe_eval(expression)
        
        # Check if the result length is within limits
        result_str = str(result)
        if len(result_str) > MAX_OUTPUT_LENGTH:
            error_message = f"Result exceeds the maximum allowed length of {MAX_OUTPUT_LENGTH} characters."
            logger.error(error_message)
            return error_message

        # result_message = f"The result of `{expression}` is `{result}`."
        result_message = f"The result of <code>{expression}</code> is <code>{result}</code>."
        
        logger.info(f"Calculation successful: {result_message}")
        return result_message
    except Exception as e:
        error_message = f"Error evaluating expression `{expression}`: {str(e)}"
        logger.error(error_message)
        return error_message
