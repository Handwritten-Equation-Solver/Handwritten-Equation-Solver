from sympy import *
from sympy.abc import *
from sympy.parsing.sympy_parser import parse_expr

def solveIt(equation):
    solution = "Error occured while Solving Equation"
    try:
        solution = str(solveset(equation))
        return solution
    except:
        return solution
    
def solveSystem(equations):
    parsed_equations = []
    for equation in equations:
        parsed_equations.append(parse_expr(equation))
    try:
        result = str(solve(parsed_equations))
        return result
    except:
        return result
