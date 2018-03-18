from wolframhelper import solver
import sys

equation = ''.join(sys.argv[1:])
solver.find_solution(equation)
