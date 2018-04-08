from sympy import plot_implicit
import sys
import os

graph = plot_implicit(sys.argv[1])
graph.save("graph.png")

result = {'dummy'}
print(json.dumps(result))
sys.stdout.flush()
