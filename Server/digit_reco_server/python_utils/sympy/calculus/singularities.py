"""
Singularities
=============

This module implements algorithms for finding singularities for a function
and identifying types of functions.

The differential calculus methods in this module include methods to identify
the following function types in the given ``Interval``:
- Increasing
- Strictly Increasing
- Decreasing
- Strictly Decreasing
- Monotonic

"""

from sympy.core.sympify import sympify
from sympy.solvers.solveset import solveset
from sympy.simplify import simplify
from sympy import S, Symbol


def singularities(expression, symbol):
    """
    Find singularities of a given function.

    Currently supported functions are:
    - univariate rational (real or complex) functions

    Examples
    ========

    >>> from sympy.calculus.singularities import singularities
    >>> from sympy import Symbol
    >>> x = Symbol('x', real=True)
    >>> y = Symbol('y', real=False)
    >>> singularities(x**2 + x + 1, x)
    EmptySet()
    >>> singularities(1/(x + 1), x)
    {-1}
    >>> singularities(1/(y**2 + 1), y)
    {-I, I}
    >>> singularities(1/(y**3 + 1), y)
    {-1, 1/2 - sqrt(3)*I/2, 1/2 + sqrt(3)*I/2}

    Notes
    =====

    This function does not find nonisolated singularities
    nor does it find branch points of the expression.

    References
    ==========

    .. [1] http://en.wikipedia.org/wiki/Mathematical_singularity

    """
    if not expression.is_rational_function(symbol):
        raise NotImplementedError(
            "Algorithms finding singularities for non-rational"
            " functions are not yet implemented."
        )
    else:
        return solveset(simplify(1 / expression), symbol)


###########################################################################
###################### DIFFERENTIAL CALCULUS METHODS ######################
###########################################################################


def monotonicity_helper(expression, predicate, interval=S.Reals, symbol=None):
    """
    Helper function for functions checking function monotonicity.

    It returns a boolean indicating whether the interval in which
    the function's derivative satisfies given predicate is a superset
    of the given interval.
    """
    expression = sympify(expression)
    free = expression.free_symbols

    if symbol is None:
        if len(free) > 1:
            raise NotImplementedError(
                'The function has not yet been implemented'
                ' for all multivariate expressions.'
            )

    x = symbol or (free.pop() if free else Symbol('x'))
    derivative = expression.diff(x)
    predicate_interval = solveset(predicate(derivative), x, S.Reals)
    return interval.is_subset(predicate_interval)


def is_increasing(expression, interval=S.Reals, symbol=None):
    """
    Return whether the function is increasing in the given interval.

    Examples
    ========

    >>> from sympy import is_increasing
    >>> from sympy.abc import x, y
    >>> from sympy import S, Interval, oo
    >>> is_increasing(x**3 - 3*x**2 + 4*x, S.Reals)
    True
    >>> is_increasing(-x**2, Interval(-oo, 0))
    True
    >>> is_increasing(-x**2, Interval(0, oo))
    False
    >>> is_increasing(4*x**3 - 6*x**2 - 72*x + 30, Interval(-2, 3))
    False
    >>> is_increasing(x**2 + y, Interval(1, 2), x)
    True

    """
    return monotonicity_helper(expression, lambda x: x >= 0, interval, symbol)


def is_strictly_increasing(expression, interval=S.Reals, symbol=None):
    """
    Return whether the function is strictly increasing in the given interval.

    Examples
    ========

    >>> from sympy import is_strictly_increasing
    >>> from sympy.abc import x, y
    >>> from sympy import Interval, oo
    >>> is_strictly_increasing(4*x**3 - 6*x**2 - 72*x + 30, Interval.Ropen(-oo, -2))
    True
    >>> is_strictly_increasing(4*x**3 - 6*x**2 - 72*x + 30, Interval.Lopen(3, oo))
    True
    >>> is_strictly_increasing(4*x**3 - 6*x**2 - 72*x + 30, Interval.open(-2, 3))
    False
    >>> is_strictly_increasing(-x**2, Interval(0, oo))
    False
    >>> is_strictly_increasing(-x**2 + y, Interval(-oo, 0), x)
    False

    """
    return monotonicity_helper(expression, lambda x: x > 0, interval, symbol)


def is_decreasing(expression, interval=S.Reals, symbol=None):
    """
    Return whether the function is decreasing in the given interval.

    Examples
    ========

    >>> from sympy import is_decreasing
    >>> from sympy.abc import x, y
    >>> from sympy import S, Interval, oo
    >>> is_decreasing(1/(x**2 - 3*x), Interval.open(1.5, 3))
    True
    >>> is_decreasing(1/(x**2 - 3*x), Interval.Lopen(3, oo))
    True
    >>> is_decreasing(1/(x**2 - 3*x), Interval.Ropen(-oo, S(3)/2))
    False
    >>> is_decreasing(-x**2, Interval(-oo, 0))
    False
    >>> is_decreasing(-x**2 + y, Interval(-oo, 0), x)
    False

    """
    return monotonicity_helper(expression, lambda x: x <= 0, interval, symbol)


def is_strictly_decreasing(expression, interval=S.Reals, symbol=None):
    """
    Return whether the function is strictly decreasing in the given interval.

    Examples
    ========

    >>> from sympy import is_strictly_decreasing
    >>> from sympy.abc import x, y
    >>> from sympy import S, Interval, oo
    >>> is_strictly_decreasing(1/(x**2 - 3*x), Interval.Lopen(3, oo))
    True
    >>> is_strictly_decreasing(1/(x**2 - 3*x), Interval.Ropen(-oo, S(3)/2))
    False
    >>> is_strictly_decreasing(-x**2, Interval(-oo, 0))
    False
    >>> is_strictly_decreasing(-x**2 + y, Interval(-oo, 0), x)
    False

    """
    return monotonicity_helper(expression, lambda x: x < 0, interval, symbol)


def is_monotonic(expression, interval=S.Reals, symbol=None):
    """
    Return whether the function is monotonic in the given interval.

    Examples
    ========

    >>> from sympy import is_monotonic
    >>> from sympy.abc import x, y
    >>> from sympy import S, Interval, oo
    >>> is_monotonic(1/(x**2 - 3*x), Interval.open(1.5, 3))
    True
    >>> is_monotonic(1/(x**2 - 3*x), Interval.Lopen(3, oo))
    True
    >>> is_monotonic(x**3 - 3*x**2 + 4*x, S.Reals)
    True
    >>> is_monotonic(-x**2, S.Reals)
    False
    >>> is_monotonic(x**2 + y + 1, Interval(1, 2), x)
    True

    """
    expression = sympify(expression)

    free = expression.free_symbols
    if symbol is None and len(free) > 1:
        raise NotImplementedError(
            'is_monotonic has not yet been implemented'
            ' for all multivariate expressions.'
        )

    x = symbol or (free.pop() if free else Symbol('x'))
    turning_points = solveset(expression.diff(x), x, interval)
    return interval.intersection(turning_points) is S.EmptySet
