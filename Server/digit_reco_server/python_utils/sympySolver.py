from sympy import *
from sympy.abc import *

def solveIt(equation):
    solution = "Error occured while Solving Equation"
    try:
        solution = str(solveset(equation))
        return solution
    except:
        return solution