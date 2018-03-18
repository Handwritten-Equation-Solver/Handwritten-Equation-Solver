from sympy import symbols, sin, Matrix, Interval, Piecewise, Sum, lambdify,Expr
from sympy.utilities.pytest import raises

from sympy.printing.lambdarepr import lambdarepr, LambdaPrinter, TensorflowPrinter, NumExprPrinter


x, y, z = symbols("x,y,z")
i, a, b = symbols("i,a,b")
j, c, d = symbols("j,c,d")


def test_basic():
    assert lambdarepr(x*y) == "x*y"
    assert lambdarepr(x + y) in ["y + x", "x + y"]
    assert lambdarepr(x**y) == "x**y"


def test_matrix():
    A = Matrix([[x, y], [y*x, z**2]])
    # assert lambdarepr(A) == "ImmutableDenseMatrix([[x, y], [x*y, z**2]])"
    # Test printing a Matrix that has an element that is printed differently
    # with the LambdaPrinter than in the StrPrinter.
    p = Piecewise((x, True), evaluate=False)
    A = Matrix([p])
    assert lambdarepr(A) == "ImmutableDenseMatrix([[((x))]])"


def test_piecewise():
    # In each case, test eval() the lambdarepr() to make sure there are a
    # correct number of parentheses. It will give a SyntaxError if there aren't.

    h = "lambda x: "

    p = Piecewise((x, True), evaluate=False)
    l = lambdarepr(p)
    eval(h + l)
    assert l == "((x))"

    p = Piecewise((x, x < 0))
    l = lambdarepr(p)
    eval(h + l)
    assert l == "((x) if (x < 0) else None)"

    p = Piecewise(
        (1, x < 1),
        (2, x < 2),
        (0, True)
    )
    l = lambdarepr(p)
    eval(h + l)
    assert l == "((1) if (x < 1) else (2) if (x < 2) else (0))"

    p = Piecewise(
        (1, x < 1),
        (2, x < 2),
    )
    l = lambdarepr(p)
    eval(h + l)
    assert l == "((1) if (x < 1) else (2) if (x < 2) else None)"

    p = Piecewise(
        (x, x < 1),
        (x**2, Interval(3, 4, True, False).contains(x)),
        (0, True),
    )
    l = lambdarepr(p)
    eval(h + l)
    assert l == "((x) if (x < 1) else (x**2) if (((x <= 4)) and ((x > 3))) else (0))"

    p = Piecewise(
        (x**2, x < 0),
        (x, x < 1),
        (2 - x, x >= 1),
        (0, True), evaluate=False
    )
    l = lambdarepr(p)
    eval(h + l)
    assert l == "((x**2) if (x < 0) else (x) if (x < 1)"\
                                " else (-x + 2) if (x >= 1) else (0))"

    p = Piecewise(
        (x**2, x < 0),
        (x, x < 1),
        (2 - x, x >= 1), evaluate=False
    )
    l = lambdarepr(p)
    eval(h + l)
    assert l == "((x**2) if (x < 0) else (x) if (x < 1)"\
                    " else (-x + 2) if (x >= 1) else None)"

    p = Piecewise(
        (1, x >= 1),
        (2, x >= 2),
        (3, x >= 3),
        (4, x >= 4),
        (5, x >= 5),
        (6, True)
    )
    l = lambdarepr(p)
    eval(h + l)
    assert l == "((1) if (x >= 1) else (2) if (x >= 2) else (3) if (x >= 3)"\
                        " else (4) if (x >= 4) else (5) if (x >= 5) else (6))"

    p = Piecewise(
        (1, x <= 1),
        (2, x <= 2),
        (3, x <= 3),
        (4, x <= 4),
        (5, x <= 5),
        (6, True)
    )
    l = lambdarepr(p)
    eval(h + l)
    assert l == "((1) if (x <= 1) else (2) if (x <= 2) else (3) if (x <= 3)"\
                            " else (4) if (x <= 4) else (5) if (x <= 5) else (6))"

    p = Piecewise(
        (1, x > 1),
        (2, x > 2),
        (3, x > 3),
        (4, x > 4),
        (5, x > 5),
        (6, True)
    )
    l = lambdarepr(p)
    eval(h + l)
    assert l =="((1) if (x > 1) else (2) if (x > 2) else (3) if (x > 3)"\
                            " else (4) if (x > 4) else (5) if (x > 5) else (6))"

    p = Piecewise(
        (1, x < 1),
        (2, x < 2),
        (3, x < 3),
        (4, x < 4),
        (5, x < 5),
        (6, True)
    )
    l = lambdarepr(p)
    eval(h + l)
    assert l == "((1) if (x < 1) else (2) if (x < 2) else (3) if (x < 3)"\
                            " else (4) if (x < 4) else (5) if (x < 5) else (6))"

    p = Piecewise(
        (Piecewise(
            (1, x > 0),
            (2, True)
        ), y > 0),
        (3, True)
    )
    l = lambdarepr(p)
    eval(h + l)
    assert l == "((((1) if (x > 0) else (2))) if (y > 0) else (3))"


def test_sum__1():
    # In each case, test eval() the lambdarepr() to make sure that
    # it evaluates to the same results as the symbolic expression
    s = Sum(x ** i, (i, a, b))
    l = lambdarepr(s)
    assert l == "(builtins.sum(x**i for i in range(a, b+1)))"

    args = x, a, b
    f = lambdify(args, s)
    v = 2, 3, 8
    assert f(*v) == s.subs(zip(args, v)).doit()

def test_sum__2():
    s = Sum(i * x, (i, a, b))
    l = lambdarepr(s)
    assert l == "(builtins.sum(i*x for i in range(a, b+1)))"

    args = x, a, b
    f = lambdify(args, s)
    v = 2, 3, 8
    assert f(*v) == s.subs(zip(args, v)).doit()


def test_multiple_sums():
    s = Sum(i * x + j, (i, a, b), (j, c, d))

    l = lambdarepr(s)
    assert l == "(builtins.sum(i*x + j for i in range(a, b+1) for j in range(c, d+1)))"

    args = x, a, b, c, d
    f = lambdify(args, s)
    vals = 2, 3, 4, 5, 6
    f_ref = s.subs(zip(args, vals)).doit()
    f_res = f(*vals)
    assert f_res == f_ref


def test_settings():
    raises(TypeError, lambda: lambdarepr(sin(x), method="garbage"))


class CustomPrintedObject(Expr):
    def _lambdacode(self, printer):
        return 'lambda'

    def _tensorflowcode(self, printer):
        return 'tensorflow'

    def _numpycode(self, printer):
        return 'numpy'

    def _numexprcode(self, printer):
        return 'numexpr'

    def _mpmathcode(self, printer):
        return 'mpmath'


def test_printmethod():
    # In each case, printmethod is called to test
    # its working

    obj = CustomPrintedObject()
    assert LambdaPrinter().doprint(obj) == 'lambda'
    assert TensorflowPrinter().doprint(obj) == 'tensorflow'
    assert NumExprPrinter().doprint(obj) == "evaluate('numexpr', truediv=True)"
